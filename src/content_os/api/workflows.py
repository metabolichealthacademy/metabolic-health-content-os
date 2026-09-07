"""Workflow lifecycle API."""

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from content_os.config import get_settings
from content_os.models.workflow import Workflow, WorkflowCreate, WorkflowEvent, WorkflowStage
from content_os.orchestration.orchestrator import InvalidTransitionError, Orchestrator
from content_os.persistence.database import get_engine, initialize_database
from content_os.persistence.repository import ConcurrentUpdateError, SqlWorkflowRepository

router = APIRouter(prefix="/workflows", tags=["workflows"])
orchestrator = Orchestrator()
initialize_database(get_engine(), get_settings().app_environment)
store = SqlWorkflowRepository(get_engine())


class RejectionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    actor_id: str = Field(min_length=3, max_length=128)


class ApprovalRequest(BaseModel):
    actor_id: str = Field(min_length=3, max_length=128)


def _get_workflow(workflow_id: UUID) -> Workflow:
    workflow = store.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


def _run_transition(operation: Callable[[Workflow], Workflow], workflow: Workflow) -> Workflow:
    try:
        return store.save(operation(workflow))
    except (InvalidTransitionError, ConcurrentUpdateError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("", response_model=Workflow, status_code=201)
def create_workflow(request: WorkflowCreate) -> Workflow:
    workflow = Workflow(**request.model_dump())
    workflow.history.append(
        WorkflowEvent(
            action="create",
            from_stage=WorkflowStage.RESEARCH,
            to_stage=WorkflowStage.RESEARCH,
        )
    )
    return store.create(workflow)


@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: UUID) -> Workflow:
    return _get_workflow(workflow_id)


@router.post("/{workflow_id}/advance", response_model=Workflow)
def advance_workflow(workflow_id: UUID) -> Workflow:
    workflow = _get_workflow(workflow_id)
    return _run_transition(orchestrator.advance, workflow)


@router.post("/{workflow_id}/approve", response_model=Workflow)
def approve_workflow(workflow_id: UUID, request: ApprovalRequest) -> Workflow:
    workflow = _get_workflow(workflow_id)
    return _run_transition(lambda item: orchestrator.approve(item, request.actor_id), workflow)


@router.post("/{workflow_id}/reject", response_model=Workflow)
def reject_workflow(workflow_id: UUID, request: RejectionRequest) -> Workflow:
    workflow = _get_workflow(workflow_id)
    return _run_transition(
        lambda item: orchestrator.reject(item, request.reason, request.actor_id), workflow
    )
