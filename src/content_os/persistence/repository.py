"""Transactional workflow repository with optimistic locking."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from content_os.models.workflow import Workflow, WorkflowEvent
from content_os.persistence.tables import WorkflowEventRow, WorkflowRow


class ConcurrentUpdateError(RuntimeError):
    """Raised when a stale workflow attempts to overwrite a newer version."""


class SqlWorkflowRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, workflow: Workflow) -> Workflow:
        now = datetime.now(UTC)
        workflow.version = 1
        workflow.created_at = now
        workflow.updated_at = now
        row = self._to_row(workflow)
        with Session(self.engine) as session, session.begin():
            session.add(row)
            self._append_events(session, workflow, start_sequence=0)
        return workflow

    def save(self, workflow: Workflow) -> Workflow:
        expected_version = workflow.version
        now = datetime.now(UTC)
        values = {
            "stage": workflow.stage.value,
            "status": workflow.status.value,
            "artifacts": workflow.artifacts,
            "revision_count": workflow.revision_count,
            "version": expected_version + 1,
            "updated_at": now,
        }
        with Session(self.engine) as session, session.begin():
            result = session.execute(
                update(WorkflowRow)
                .where(WorkflowRow.id == str(workflow.id), WorkflowRow.version == expected_version)
                .values(**values)
            )
            if result.rowcount != 1:
                raise ConcurrentUpdateError("Workflow was changed by another request")
            event_count = session.scalar(
                select(func.count())
                .select_from(WorkflowEventRow)
                .where(WorkflowEventRow.workflow_id == str(workflow.id))
            )
            self._append_events(session, workflow, start_sequence=int(event_count or 0))
        workflow.version = expected_version + 1
        workflow.updated_at = now
        return workflow

    def get(self, workflow_id: UUID) -> Workflow | None:
        with Session(self.engine) as session:
            row = session.get(WorkflowRow, str(workflow_id))
            if row is None:
                return None
            return self._from_row(row)

    @staticmethod
    def _to_row(workflow: Workflow) -> WorkflowRow:
        return WorkflowRow(
            id=str(workflow.id),
            topic=workflow.topic,
            audience=workflow.audience,
            sources=[item.model_dump(mode="json") for item in workflow.sources],
            claims=[item.model_dump(mode="json") for item in workflow.claims],
            stage=workflow.stage.value,
            status=workflow.status.value,
            artifacts=workflow.artifacts,
            revision_count=workflow.revision_count,
            version=workflow.version,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    @staticmethod
    def _from_row(row: WorkflowRow) -> Workflow:
        return Workflow(
            id=row.id,
            topic=row.topic,
            audience=row.audience,
            sources=row.sources,
            claims=row.claims,
            stage=row.stage,
            status=row.status,
            artifacts=row.artifacts,
            history=[
                WorkflowEvent(
                    timestamp=event.timestamp,
                    action=event.action,
                    from_stage=event.from_stage,
                    to_stage=event.to_stage,
                    note=event.note,
                    actor_id=event.actor_id,
                )
                for event in row.events
            ],
            revision_count=row.revision_count,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _append_events(session: Session, workflow: Workflow, start_sequence: int) -> None:
        for sequence, event in enumerate(
            workflow.history[start_sequence:], start=start_sequence + 1
        ):
            session.add(
                WorkflowEventRow(
                    workflow_id=str(workflow.id),
                    sequence=sequence,
                    timestamp=event.timestamp,
                    action=event.action,
                    from_stage=event.from_stage.value,
                    to_stage=event.to_stage.value,
                    note=event.note,
                    actor_id=event.actor_id,
                )
            )
