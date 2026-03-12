"""Governance schemas for proposal/project lifecycle contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openqilin.control_plane.governance.project_lifecycle import (
    ProjectLifecycleError,
    ProjectStatus,
    assert_project_transition,
)


class ProjectLifecycleTransitionRequest(BaseModel):
    """Lifecycle transition request contract for governance APIs."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    from_status: ProjectStatus
    to_status: ProjectStatus
    reason_code: str = Field(default="governance_transition", min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_transition(self) -> "ProjectLifecycleTransitionRequest":
        """Ensure requested transition matches canonical project lifecycle."""

        try:
            assert_project_transition(self.from_status, self.to_status)
        except ProjectLifecycleError as error:
            raise ValueError(f"{error.code}: {error.message}") from error
        return self


class ProjectLifecycleTransitionData(BaseModel):
    """Transition result payload for governance APIs."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    previous_status: ProjectStatus
    status: ProjectStatus
    trace_id: str


class GovernanceTransitionResponse(BaseModel):
    """Canonical governance transition response envelope."""

    model_config = ConfigDict(extra="forbid")

    status: str
    data: ProjectLifecycleTransitionData | None = None
    error: dict[str, str] | None = None
