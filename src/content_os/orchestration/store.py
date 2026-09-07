"""Replaceable in-memory workflow store for the foundation phase."""

from uuid import UUID

from content_os.models.workflow import Workflow


class WorkflowStore:
    def __init__(self) -> None:
        self._items: dict[UUID, Workflow] = {}

    def save(self, workflow: Workflow) -> Workflow:
        self._items[workflow.id] = workflow
        return workflow

    def get(self, workflow_id: UUID) -> Workflow | None:
        return self._items.get(workflow_id)
