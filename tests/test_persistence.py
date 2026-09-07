from pathlib import Path

import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from content_os.models.workflow import Workflow, WorkflowEvent, WorkflowStage
from content_os.persistence.database import build_engine, initialize_database
from content_os.persistence.repository import ConcurrentUpdateError, SqlWorkflowRepository
from content_os.persistence.tables import WorkflowEventRow, WorkflowRow


@pytest.fixture
def repository(tmp_path: Path) -> SqlWorkflowRepository:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    initialize_database(engine)
    return SqlWorkflowRepository(engine)


def test_workflow_survives_new_repository_instance(
    repository: SqlWorkflowRepository,
) -> None:
    workflow = Workflow(topic="Persistent topic", audience="general public", sources=[], claims=[])
    workflow.history.append(
        WorkflowEvent(
            action="create",
            from_stage=WorkflowStage.RESEARCH,
            to_stage=WorkflowStage.RESEARCH,
        )
    )
    repository.create(workflow)

    loaded = SqlWorkflowRepository(repository.engine).get(workflow.id)

    assert loaded is not None
    assert loaded.topic == "Persistent topic"
    assert loaded.version == 1
    assert [event.action for event in loaded.history] == ["create"]


def test_save_appends_audit_event_and_increments_version(
    repository: SqlWorkflowRepository,
) -> None:
    workflow = Workflow(topic="Audit topic", audience="general public", sources=[], claims=[])
    repository.create(workflow)
    workflow.stage = WorkflowStage.EVIDENCE
    workflow.history.append(
        WorkflowEvent(
            action="advance",
            from_stage=WorkflowStage.RESEARCH,
            to_stage=WorkflowStage.EVIDENCE,
        )
    )

    repository.save(workflow)
    loaded = repository.get(workflow.id)

    assert loaded is not None
    assert loaded.version == 2
    assert [event.action for event in loaded.history] == ["advance"]
    with Session(repository.engine) as session:
        stored_events = session.scalars(select(WorkflowEventRow)).all()
    assert len(stored_events) == 1


def test_stale_version_is_rejected(repository: SqlWorkflowRepository) -> None:
    workflow = Workflow(topic="Concurrent topic", audience="general public", sources=[], claims=[])
    repository.create(workflow)
    first_copy = repository.get(workflow.id)
    stale_copy = repository.get(workflow.id)
    assert first_copy is not None and stale_copy is not None

    first_copy.stage = WorkflowStage.EVIDENCE
    repository.save(first_copy)
    stale_copy.stage = WorkflowStage.CONTENT

    with pytest.raises(ConcurrentUpdateError, match="another request"):
        repository.save(stale_copy)


def test_repository_has_no_audit_update_or_delete_api(
    repository: SqlWorkflowRepository,
) -> None:
    assert not hasattr(repository, "update_event")
    assert not hasattr(repository, "delete_event")


def test_production_initialization_does_not_bypass_migrations(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'production.db'}")

    initialize_database(engine, environment="production")

    assert inspect(engine).get_table_names() == []


def test_audit_history_restricts_parent_workflow_deletion(
    repository: SqlWorkflowRepository,
) -> None:
    workflow = Workflow(topic="Retained topic", audience="general public", sources=[], claims=[])
    workflow.history.append(
        WorkflowEvent(
            action="create",
            from_stage=WorkflowStage.RESEARCH,
            to_stage=WorkflowStage.RESEARCH,
        )
    )
    repository.create(workflow)

    with pytest.raises(IntegrityError), Session(repository.engine) as session, session.begin():
        session.execute(delete(WorkflowRow).where(WorkflowRow.id == str(workflow.id)))
