"""Document-policy enforcement helpers for the administrator agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, cast
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.artifact_file_store import ArtifactFileStore, ArtifactFileStoreError
from openqilin.data_access.repositories.artifacts import (
    _GOVERNANCE_EVENT_ARTIFACT_TYPES,
    ProjectArtifactPointer,
    ProjectArtifactRepositoryError,
)

if TYPE_CHECKING:
    from openqilin.agents.auditor.enforcement import AuditWriter
    from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
        PostgresGovernanceArtifactRepository,
    )


@dataclass(frozen=True, slots=True)
class CapCheckResult:
    """Result of a per-type and total-cap check."""

    allowed: bool
    denial_code: str | None
    denial_reason: str | None


@dataclass(frozen=True, slots=True)
class HashIntegrityResult:
    """Result of a content-hash integrity check."""

    integrity_ok: bool
    denial_reason: str | None


class DocumentPolicyEnforcer:
    """Pre-write gate for document caps, write permissions, and hash integrity."""

    def __init__(
        self,
        governance_repo: "PostgresGovernanceArtifactRepository",
        audit_writer: "AuditWriter",
        trace_id_factory: Callable[[], str] | None = None,
        artifact_file_store: ArtifactFileStore | None = None,
    ) -> None:
        self._governance_repo = governance_repo
        self._audit_writer = audit_writer
        self._session_factory = cast(
            sessionmaker[Session] | None,
            getattr(governance_repo, "_session_factory", None),
        )
        self._trace_id_factory = trace_id_factory or (lambda: str(uuid4()))
        self._artifact_file_store = artifact_file_store

    def check_artifact_cap(
        self,
        *,
        project_id: str,
        artifact_type: str,
        trace_id: str,
    ) -> CapCheckResult:
        """Check per-type cap and total-cap before an artifact create."""

        normalized_project_id = project_id.strip()
        normalized_artifact_type = artifact_type.strip().lower()
        try:
            per_type_cap = self._governance_repo.policy.cap_for_type(normalized_artifact_type)
            current_count = len(
                _list_pointers_for_type(
                    governance_repo=self._governance_repo,
                    project_id=normalized_project_id,
                    artifact_type=normalized_artifact_type,
                )
            )
            if current_count >= per_type_cap:
                return CapCheckResult(
                    allowed=False,
                    denial_code="artifact_type_cap_exceeded",
                    denial_reason=(
                        "artifact_type active-document cap exceeded: "
                        f"{normalized_artifact_type} ({current_count}/{per_type_cap})"
                    ),
                )
            if normalized_artifact_type not in _GOVERNANCE_EVENT_ARTIFACT_TYPES:
                total_count = _count_project_artifacts(
                    project_id=normalized_project_id,
                    session_factory=self._session_factory,
                    governance_repo=self._governance_repo,
                )
                if total_count >= self._governance_repo.policy.total_active_document_cap:
                    return CapCheckResult(
                        allowed=False,
                        denial_code="artifact_project_document_cap_exceeded",
                        denial_reason=(
                            "project total active-document cap exceeded: "
                            f"({total_count}/{self._governance_repo.policy.total_active_document_cap})"
                        ),
                    )
        except ProjectArtifactRepositoryError as exc:
            return CapCheckResult(
                allowed=False,
                denial_code=exc.code,
                denial_reason=exc.message,
            )
        except Exception as exc:
            return CapCheckResult(
                allowed=False,
                denial_code="artifact_cap_check_failed",
                denial_reason=str(exc),
            )
        return CapCheckResult(allowed=True, denial_code=None, denial_reason=None)

    def check_role_permission(
        self,
        *,
        actor_role: str,
        artifact_type: str,
        project_status: str,
    ) -> bool:
        """Return True if actor_role may write artifact_type in project_status."""

        normalized_role = actor_role.strip().lower()
        normalized_type = artifact_type.strip().lower()
        normalized_status = project_status.strip().lower()
        if normalized_status not in {"proposed", "approved", "active", "paused"}:
            return False
        if normalized_role == "project_manager" and normalized_type in {
            "project_charter",
            "workforce_plan",
        }:
            return False
        if normalized_role in {"owner", "ceo", "cwo", "auditor", "administrator"}:
            return True
        if normalized_role == "project_manager":
            return True
        return False

    def check_hash_integrity(
        self,
        *,
        stored_hash: str | None,
        provided_hash: str | None,
        trace_id: str,
    ) -> HashIntegrityResult:
        """Compare provided_hash against stored_hash."""

        effective_trace_id = trace_id or self._trace_id_factory()
        if provided_hash is None:
            return HashIntegrityResult(integrity_ok=True, denial_reason=None)
        if stored_hash is None:
            return HashIntegrityResult(integrity_ok=True, denial_reason=None)
        if provided_hash != stored_hash:
            self._audit_writer.write_event(
                event_type="hash_integrity_failure",
                outcome="denied",
                trace_id=effective_trace_id,
                request_id=None,
                task_id=None,
                principal_id="administrator",
                principal_role="administrator",
                source="administrator",
                reason_code="hash_integrity_failure",
                message="content_hash mismatch",
                policy_version="v2",
                policy_hash="administrator-v1",
                rule_ids=["STR-007", "STR-010"],
                payload={
                    "stored_hash": stored_hash,
                    "provided_hash": provided_hash,
                },
            )
            return HashIntegrityResult(
                integrity_ok=False,
                denial_reason=(
                    f"content_hash mismatch: stored={stored_hash!r}, provided={provided_hash!r}"
                ),
            )
        return HashIntegrityResult(integrity_ok=True, denial_reason=None)

    def verify_storage_uri_hash(
        self,
        *,
        storage_uri: str,
        db_content_hash: str,
        trace_id: str,
    ) -> HashIntegrityResult:
        """Verify file at storage_uri has hash matching db_content_hash."""

        if self._artifact_file_store is None:
            return HashIntegrityResult(integrity_ok=True, denial_reason=None)

        effective_trace_id = trace_id or self._trace_id_factory()

        try:
            content = self._artifact_file_store.read(storage_uri)
        except ArtifactFileStoreError as exc:
            self._audit_writer.write_event(
                event_type="hash_integrity_failure",
                outcome="denied",
                trace_id=effective_trace_id,
                request_id=None,
                task_id=None,
                principal_id="administrator",
                principal_role="administrator",
                source="administrator",
                reason_code="artifact_file_store_read_error",
                message=exc.message,
                policy_version="v2",
                policy_hash="administrator-v1",
                rule_ids=["STR-007", "STR-010"],
                payload={
                    "storage_uri": storage_uri,
                    "db_content_hash": db_content_hash,
                    "error": exc.code,
                },
            )
            return HashIntegrityResult(
                integrity_ok=False,
                denial_reason=f"file read error: {exc.message}",
            )

        file_hash = self._artifact_file_store.compute_hash(content)
        if file_hash != db_content_hash:
            self._audit_writer.write_event(
                event_type="hash_integrity_failure",
                outcome="denied",
                trace_id=effective_trace_id,
                request_id=None,
                task_id=None,
                principal_id="administrator",
                principal_role="administrator",
                source="administrator",
                reason_code="hash_integrity_failure",
                message="content_hash mismatch",
                policy_version="v2",
                policy_hash="administrator-v1",
                rule_ids=["STR-007", "STR-010"],
                payload={
                    "storage_uri": storage_uri,
                    "db_content_hash": db_content_hash,
                    "file_hash": file_hash,
                },
            )
            return HashIntegrityResult(
                integrity_ok=False,
                denial_reason=f"content_hash mismatch: db={db_content_hash!r}, file={file_hash!r}",
            )

        return HashIntegrityResult(integrity_ok=True, denial_reason=None)


def _count_project_artifacts(
    *,
    project_id: str,
    session_factory: sessionmaker[Session] | None,
    governance_repo: object,
) -> int:
    if session_factory is not None:
        with session_factory() as session:
            row = (
                session.execute(
                    text("SELECT COUNT(*) AS cnt FROM artifacts WHERE project_id = :project_id"),
                    {"project_id": project_id},
                )
                .mappings()
                .first()
            )
        return int((row or {}).get("cnt", 0))  # type: ignore[call-overload]
    if hasattr(governance_repo, "list_project_artifacts"):
        repo = cast(Any, governance_repo)
        return len(repo.list_project_artifacts(project_id))
    raise RuntimeError("governance repository does not support project artifact counting")


def _list_pointers_for_type(
    *,
    governance_repo: object,
    project_id: str,
    artifact_type: str,
) -> tuple[ProjectArtifactPointer, ...]:
    if hasattr(governance_repo, "list_project_artifacts"):
        repo = cast(Any, governance_repo)
        return tuple(repo.list_project_artifacts(project_id, artifact_type=artifact_type))
    repo = cast("PostgresGovernanceArtifactRepository", governance_repo)
    return repo.list_pointers(project_id=project_id, artifact_type=artifact_type)
