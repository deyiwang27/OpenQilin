"""Governance schemas for proposal/project lifecycle contracts."""

from __future__ import annotations

from typing import Any, Literal

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


class ProposalDiscussionRequest(BaseModel):
    """Proposal discussion message payload."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)


class ProjectCreateRequest(BaseModel):
    """Project creation payload for proposal-stage governance kickoff."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    objective: str = Field(min_length=1, max_length=4000)
    project_id: str | None = Field(default=None, min_length=1, max_length=128)
    metadata: dict[str, str] = Field(default_factory=dict)


class ProposalApprovalRequest(BaseModel):
    """Proposal approval payload."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)


class ProjectCompletionReportRequest(BaseModel):
    """Project Manager completion report payload."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=8000)
    metric_results: dict[str, str] = Field(default_factory=dict)


class ProjectCompletionApprovalRequest(BaseModel):
    """C-suite completion approval payload."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)


class ProjectCompletionFinalizeRequest(BaseModel):
    """Completion finalization payload once governance chain is satisfied."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    reason_code: str = Field(
        default="completion_approved_by_cwo_ceo",
        min_length=1,
        max_length=128,
    )


class ProjectInitializationRequest(BaseModel):
    """CWO project initialization payload."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    objective: str = Field(min_length=1, max_length=4000)
    budget_currency_total: float = Field(ge=0)
    budget_quota_total: float = Field(ge=0)
    metric_plan: dict[str, str] = Field(default_factory=dict)
    workforce_plan: dict[str, str] = Field(default_factory=dict)


class WorkforceTemplateBindingRequest(BaseModel):
    """CWO workforce template binding payload."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(min_length=1, max_length=128)
    role: Literal["project_manager", "domain_leader"]
    template_id: str = Field(min_length=1, max_length=128)
    llm_routing_profile: str = Field(min_length=1, max_length=128)
    system_prompt: str = Field(min_length=1, max_length=20000)


class GovernanceApiError(BaseModel):
    """Canonical governance API error payload."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool
    source_component: str
    details: dict[str, Any] = Field(default_factory=dict)


class GovernanceApiResponse(BaseModel):
    """Canonical governance API response envelope."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    status: Literal["ok", "denied", "error"]
    data: dict[str, Any] | None = None
    error: GovernanceApiError | None = None
