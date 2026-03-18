"""Project Manager governed artifact writer."""

from __future__ import annotations

from typing import Any

from openqilin.agents.project_manager.models import PMWriteNotAllowedError
from openqilin.data_access.repositories.artifacts import (
    ProjectArtifactPointer,
    ProjectArtifactRepositoryError,
    ProjectArtifactWriteContext,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)

DIRECT_WRITE_TYPES = frozenset(
    {"execution_plan", "risk_register", "decision_log", "progress_report"}
)
CONDITIONAL_WRITE_TYPES = frozenset({"scope_statement", "budget_plan", "success_metrics"})
PROHIBITED_TYPES = frozenset({"project_charter", "workforce_plan"})
APPEND_ONLY_TYPES = frozenset({"progress_report", "decision_log", "completion_report"})

_REQUIRED_APPROVAL_ROLES = frozenset({"ceo", "cwo"})


class PMProjectArtifactWriter:
    """Enforces the Project Manager artifact write contract before repository writes."""

    def __init__(self, *, project_artifact_repo: PostgresGovernanceArtifactRepository) -> None:
        self._project_artifact_repo = project_artifact_repo

    def write(
        self,
        project_id: str,
        artifact_type: str,
        content_md: str,
        trace_id: str,
        project_state: str,
        approval_evidence: Any = None,
    ) -> ProjectArtifactPointer:
        normalized_type = artifact_type.strip().lower()
        normalized_state = project_state.strip().lower()

        if normalized_type in PROHIBITED_TYPES:
            raise PMWriteNotAllowedError(
                f"Project Manager cannot write prohibited artifact type: {normalized_type}"
            )
        if normalized_state != "active":
            raise PMWriteNotAllowedError(
                f"Project Manager artifact writes require active project state, got: {normalized_state}"
            )
        if normalized_type in CONDITIONAL_WRITE_TYPES and not _has_non_empty_approval_evidence(
            approval_evidence
        ):
            raise PMWriteNotAllowedError(
                f"Controlled artifact writes require approval evidence: {normalized_type}"
            )

        try:
            return self._project_artifact_repo.write_project_artifact(
                project_id=project_id,
                artifact_type=normalized_type,
                content=content_md,
                write_context=ProjectArtifactWriteContext(
                    actor_role="project_manager",
                    project_status=normalized_state,
                    approval_roles=_approval_roles_from_evidence(approval_evidence),
                ),
            )
        except ProjectArtifactRepositoryError as error:
            raise PMWriteNotAllowedError(error.message) from error

    def write_completion_report(
        self,
        project_id: str,
        content_md: str,
        trace_id: str,
        project_state: str,
    ) -> ProjectArtifactPointer:
        normalized_state = project_state.strip().lower()
        if normalized_state not in {"active", "paused"}:
            raise PMWriteNotAllowedError(
                "Completion report requires project state active or paused"
            )

        try:
            return self._project_artifact_repo.write_project_artifact(
                project_id=project_id,
                artifact_type="completion_report",
                content=content_md,
                write_context=ProjectArtifactWriteContext(
                    actor_role="project_manager",
                    project_status=normalized_state,
                    approval_roles=(),
                ),
            )
        except ProjectArtifactRepositoryError as error:
            raise PMWriteNotAllowedError(error.message) from error


def _has_non_empty_approval_evidence(approval_evidence: Any) -> bool:
    if isinstance(approval_evidence, bool):
        return approval_evidence
    if isinstance(approval_evidence, str):
        return bool(approval_evidence.strip())
    if isinstance(approval_evidence, dict):
        return bool(approval_evidence)
    if isinstance(approval_evidence, (list, tuple, set, frozenset)):
        return bool(approval_evidence)
    return approval_evidence is not None


def _approval_roles_from_evidence(approval_evidence: Any) -> tuple[str, ...]:
    if isinstance(approval_evidence, dict):
        if "approval_roles" in approval_evidence:
            roles = approval_evidence.get("approval_roles")
            if isinstance(roles, (list, tuple, set, frozenset)):
                return tuple(
                    sorted(str(role).strip().lower() for role in roles if str(role).strip())
                )
        roles = tuple(
            sorted(
                role
                for role in _REQUIRED_APPROVAL_ROLES
                if bool(approval_evidence.get(role) or approval_evidence.get(f"{role}_approval"))
            )
        )
        if roles:
            return roles
    return ()
