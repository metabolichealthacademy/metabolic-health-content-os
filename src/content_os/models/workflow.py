"""Workflow state and API data contracts."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from content_os.models.evidence import ClaimCandidate, SourceCandidate


class WorkflowStage(StrEnum):
    RESEARCH = "research"
    EVIDENCE = "evidence"
    CONTENT = "content"
    SAFETY = "safety"
    PRODUCTION = "production"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    REJECTED = "rejected"


class WorkflowStatus(StrEnum):
    ACTIVE = "active"
    REVISION_REQUIRED = "revision_required"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    REJECTED = "rejected"


class WorkflowEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action: str
    from_stage: WorkflowStage
    to_stage: WorkflowStage
    note: str | None = None
    actor_id: str | None = None


class WorkflowCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    audience: str = Field(default="general public", min_length=2, max_length=100)
    sources: list[SourceCandidate] = Field(default_factory=list)
    claims: list[ClaimCandidate] = Field(default_factory=list)


class Workflow(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    topic: str
    audience: str
    sources: list[SourceCandidate]
    claims: list[ClaimCandidate]
    stage: WorkflowStage = WorkflowStage.RESEARCH
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    artifacts: dict[str, Any] = Field(default_factory=dict)
    history: list[WorkflowEvent] = Field(default_factory=list)
    revision_count: int = 0
    version: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
