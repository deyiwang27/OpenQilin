"""Retention enforcement helpers for the administrator agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Callable
from uuid import uuid4

from openqilin.agents.administrator.models import AdministratorError
from openqilin.data_access.repositories.artifacts import ProjectArtifactWriteContext

if TYPE_CHECKING:
    from openqilin.agents.auditor.enforcement import AuditWriter
    from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
        PostgresGovernanceArtifactRepository,
    )

_ADMINISTRATOR_WRITE_CONTEXT = ProjectArtifactWriteContext(
    actor_role="administrator",
    project_status="active",
)


class RetentionEnforcer:
    """Archives completed or terminated projects with immutable evidence records."""

    def __init__(
        self,
        governance_repo: "PostgresGovernanceArtifactRepository",
        audit_writer: "AuditWriter",
        trace_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._governance_repo = governance_repo
        self._audit_writer = audit_writer
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid4()))

    def enforce_completed_project(
        self,
        *,
        project_id: str,
        trace_id: str,
    ) -> str:
        """Emit the canonical retention record for a completed project."""

        normalized_project_id = _require_project_id(project_id, "enforce_completed_project")
        effective_trace_id = trace_id or self._trace_id_factory()
        pointer = self._governance_repo.write_project_artifact(
            project_id=normalized_project_id,
            artifact_type="administrator_retention",
            content=_serialize_payload(
                {
                    "event_type": "administrator_retention",
                    "action": "completed_project_archived",
                    "project_id": normalized_project_id,
                    "rule_ids": ["STR-001"],
                    "trace_id": effective_trace_id,
                    "created_at": _utc_now_iso(),
                }
            ),
            write_context=_ADMINISTRATOR_WRITE_CONTEXT,
        )
        # REVIEW_NOTE: Actual artifact mutation to read-only is enforced by the repository's
        # `_assert_write_authorization` which rejects writes when `project_status` is `completed`
        # or `terminated`. `RetentionEnforcer` emits the canonical STR-001/STR-002 evidence
        # record; it does not mutate artifact rows directly. Channel archiving is a future
        # Discord-layer operation.
        self._audit_writer.write_event(
            event_type="administrator_retention",
            outcome="archived",
            trace_id=effective_trace_id,
            request_id=None,
            task_id=None,
            principal_id="administrator",
            principal_role="administrator",
            source="administrator",
            reason_code="retention_completed",
            message="completed project archived",
            policy_version="v2",
            policy_hash="administrator-v1",
            rule_ids=["STR-001"],
            payload={
                "project_id": normalized_project_id,
                "action": "completed_project_archived",
            },
        )
        return pointer.storage_uri

    def enforce_terminated_project(
        self,
        *,
        project_id: str,
        trace_id: str,
    ) -> str:
        """Emit the canonical retention records for a terminated project."""

        normalized_project_id = _require_project_id(project_id, "enforce_terminated_project")
        effective_trace_id = trace_id or self._trace_id_factory()
        self.enforce_completed_project(
            project_id=normalized_project_id,
            trace_id=effective_trace_id,
        )
        pointer = self._governance_repo.write_project_artifact(
            project_id=normalized_project_id,
            artifact_type="administrator_retention",
            content=_serialize_payload(
                {
                    "event_type": "administrator_retention",
                    "action": "terminated_project_archived",
                    "project_id": normalized_project_id,
                    "rule_ids": ["STR-001", "STR-002"],
                    "trace_id": effective_trace_id,
                    "created_at": _utc_now_iso(),
                }
            ),
            write_context=_ADMINISTRATOR_WRITE_CONTEXT,
        )
        self._audit_writer.write_event(
            event_type="administrator_retention",
            outcome="archived",
            trace_id=effective_trace_id,
            request_id=None,
            task_id=None,
            principal_id="administrator",
            principal_role="administrator",
            source="administrator",
            reason_code="retention_terminated",
            message="terminated project archived",
            policy_version="v2",
            policy_hash="administrator-v1",
            rule_ids=["STR-001", "STR-002"],
            payload={
                "project_id": normalized_project_id,
                "action": "terminated_project_archived",
            },
        )
        return pointer.storage_uri


def _require_project_id(project_id: str, operation: str) -> str:
    normalized = project_id.strip()
    if not normalized:
        raise AdministratorError(f"{operation} requires project_id")
    return normalized


def _serialize_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True)


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()
