"""Project artifact repository with canonical file-root and pointer/hash contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ARTIFACT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

_MVP_ARTIFACT_TYPE_CAPS: Mapping[str, int] = MappingProxyType(
    {
        "project_charter": 1,
        "scope_statement": 1,
        "budget_plan": 1,
        "success_metrics": 1,
        "workforce_plan": 1,
        "execution_plan": 1,
        "decision_log": 4,
        "risk_register": 3,
        "progress_report": 6,
        "completion_report": 1,
        "cso_review": 12,
        "ceo_proposal_decision": 12,
        "ceo_coapproval": 8,
        "cwo_coapproval": 8,
        "auditor_finding": 32,
        "auditor_enforcement": 32,
        "auditor_owner_escalation": 32,
        "auditor_ceo_notification": 32,
        "auditor_owner_alert": 32,
    }
)
_MVP_PROJECT_TOTAL_ACTIVE_DOCUMENT_CAP = 20
_APPEND_ONLY_ARTIFACT_TYPES = frozenset(
    {
        "decision_log",
        "progress_report",
        "completion_report",
        "cso_review",
        "ceo_proposal_decision",
        "ceo_coapproval",
        "cwo_coapproval",
        "auditor_finding",
        "auditor_enforcement",
        "auditor_owner_escalation",
        "auditor_ceo_notification",
        "auditor_owner_alert",
    }
)
_GOVERNANCE_EVENT_ARTIFACT_TYPES = frozenset(
    {
        "cso_review",
        "ceo_proposal_decision",
        "ceo_coapproval",
        "cwo_coapproval",
    }
)
_PROJECT_WRITABLE_STATES = frozenset({"proposed", "approved", "active", "paused"})
_PROJECT_MANAGER_DIRECT_WRITE_TYPES = frozenset(
    {"execution_plan", "risk_register", "decision_log", "progress_report", "completion_report"}
)
_PROJECT_MANAGER_CONTROLLED_WRITE_TYPES = frozenset(
    {"scope_statement", "budget_plan", "success_metrics"}
)
_PROJECT_MANAGER_FORBIDDEN_WRITE_TYPES = frozenset({"project_charter", "workforce_plan"})


class ProjectArtifactRepositoryError(ValueError):
    """Raised when project artifact repository contract checks fail."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ProjectArtifactPointer:
    """Pointer/hash metadata for one project artifact revision."""

    project_id: str
    artifact_type: str
    revision_no: int
    storage_uri: str
    content_hash: str
    created_at: datetime
    byte_size: int


@dataclass(frozen=True, slots=True)
class ProjectArtifactDocument:
    """Resolved artifact document content plus pointer metadata."""

    pointer: ProjectArtifactPointer
    content: str


@dataclass(frozen=True, slots=True)
class ProjectArtifactWriteContext:
    """Authorization context required for governed project artifact writes."""

    actor_role: str
    project_status: str
    approval_roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectDocumentPolicy:
    """Project-document policy contract for allowed types and cap enforcement."""

    allowed_type_caps: Mapping[str, int]
    total_active_document_cap: int

    @staticmethod
    def mvp_defaults() -> "ProjectDocumentPolicy":
        """Return strict MVP project-document policy defaults."""

        return ProjectDocumentPolicy(
            allowed_type_caps=_MVP_ARTIFACT_TYPE_CAPS,
            total_active_document_cap=_MVP_PROJECT_TOTAL_ACTIVE_DOCUMENT_CAP,
        )

    def cap_for_type(self, artifact_type: str) -> int:
        """Resolve configured cap for one artifact type."""

        cap = self.allowed_type_caps.get(artifact_type)
        if cap is None:
            raise ProjectArtifactRepositoryError(
                code="artifact_type_not_allowed",
                message=f"artifact_type is not allowed by policy: {artifact_type}",
            )
        return cap
