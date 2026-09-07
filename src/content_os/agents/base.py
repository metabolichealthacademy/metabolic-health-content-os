"""Common interface for deterministic or provider-backed agents."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from content_os.models.workflow import Workflow, WorkflowStage


class BaseAgent(ABC):
    stage: WorkflowStage

    @abstractmethod
    def run(self, workflow: Workflow) -> BaseModel:
        """Run one bounded stage and return a validated artifact."""

    def require_artifact(self, workflow: Workflow, key: str) -> Any:
        if key not in workflow.artifacts:
            raise ValueError(f"Required artifact is missing: {key}")
        return workflow.artifacts[key]
