"""PostgreSQL-backed project artifact repository replacing InMemoryProjectArtifactRepository.

Stores artifact content directly in PostgreSQL (TEXT column) rather than on disk.
Pointer/hash semantics and governance authorization are preserved.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.repositories.artifacts import (
    ProjectArtifactDocument,
    ProjectArtifactPointer,
    ProjectArtifactRepositoryError,
    ProjectArtifactWriteContext,
    ProjectDocumentPolicy,
)

_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ARTIFACT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

_APPEND_ONLY_ARTIFACT_TYPES = frozenset({"decision_log", "progress_report", "completion_report"})
_PROJECT_WRITABLE_STATES = frozenset({"proposed", "approved", "active", "paused"})
_PROJECT_MANAGER_DIRECT_WRITE_TYPES = frozenset(
    {"execution_plan", "risk_register", "decision_log", "progress_report", "completion_report"}
)
_PROJECT_MANAGER_CONTROLLED_WRITE_TYPES = frozenset(
    {"scope_statement", "budget_plan", "success_metrics"}
)
_PROJECT_MANAGER_FORBIDDEN_WRITE_TYPES = frozenset({"project_charter", "workforce_plan"})


class PostgresGovernanceArtifactRepository:
    """PostgreSQL-backed project artifact repository with governed write authorization."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        policy: ProjectDocumentPolicy | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy or ProjectDocumentPolicy.mvp_defaults()

    @property
    def policy(self) -> ProjectDocumentPolicy:
        """Active project-document policy used by this repository."""
        return self._policy

    def write_project_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
        content: str,
        write_context: ProjectArtifactWriteContext | None = None,
    ) -> ProjectArtifactPointer:
        """Persist one artifact revision and return pointer/hash metadata."""

        if write_context is None:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_context_missing",
                message="artifact write context is required for governed writes",
            )
        normalized_project_id = _validate_project_id(project_id)
        normalized_type = _validate_artifact_type(artifact_type)
        _assert_write_authorization(artifact_type=normalized_type, write_context=write_context)

        per_type_cap = self._policy.cap_for_type(normalized_type)
        is_append_only = normalized_type in _APPEND_ONLY_ARTIFACT_TYPES

        with self._session_factory() as session:
            count_row = (
                session.execute(
                    text(
                        """
                    SELECT COUNT(*) as cnt FROM artifacts
                    WHERE project_id = :project_id AND artifact_type = :artifact_type
                    """
                    ),
                    {"project_id": normalized_project_id, "artifact_type": normalized_type},
                )
                .mappings()
                .first()
            )
            current_count = int((count_row or {}).get("cnt", 0))  # type: ignore[arg-type]

            total_count_row = (
                session.execute(
                    text("SELECT COUNT(*) as cnt FROM artifacts WHERE project_id = :project_id"),
                    {"project_id": normalized_project_id},
                )
                .mappings()
                .first()
            )
            total_count = int((total_count_row or {}).get("cnt", 0))  # type: ignore[arg-type]

        if is_append_only:
            if current_count >= per_type_cap:
                raise ProjectArtifactRepositoryError(
                    code="artifact_type_cap_exceeded",
                    message=(
                        f"artifact_type active-document cap exceeded: "
                        f"{normalized_type} ({current_count}/{per_type_cap})"
                    ),
                )
            if current_count == 0:
                _assert_total_cap(total_count, self._policy.total_active_document_cap)
            revision_no = current_count + 1
        else:
            if current_count == 0:
                _assert_total_cap(total_count, self._policy.total_active_document_cap)
            revision_no = current_count + 1

        payload = content.encode("utf-8")
        content_hash = hashlib.sha256(payload).hexdigest()
        storage_uri = f"db://artifacts/{normalized_project_id}/{normalized_type}/v{revision_no:03d}"
        now = datetime.now(tz=UTC)
        pointer = ProjectArtifactPointer(
            project_id=normalized_project_id,
            artifact_type=normalized_type,
            revision_no=revision_no,
            storage_uri=storage_uri,
            content_hash=content_hash,
            created_at=now,
            byte_size=len(payload),
        )
        from uuid import uuid4

        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO artifacts (
                        artifact_id, project_id, artifact_type, revision_no,
                        storage_uri, content_hash, content, byte_size, created_at
                    ) VALUES (
                        :artifact_id, :project_id, :artifact_type, :revision_no,
                        :storage_uri, :content_hash, :content, :byte_size, :created_at
                    )
                    ON CONFLICT (project_id, artifact_type, revision_no) DO UPDATE SET
                        content_hash = EXCLUDED.content_hash,
                        content      = EXCLUDED.content,
                        byte_size    = EXCLUDED.byte_size
                    """
                ),
                {
                    "artifact_id": str(uuid4()),
                    "project_id": normalized_project_id,
                    "artifact_type": normalized_type,
                    "revision_no": revision_no,
                    "storage_uri": storage_uri,
                    "content_hash": content_hash,
                    "content": content,
                    "byte_size": len(payload),
                    "created_at": now,
                },
            )
            session.commit()
        return pointer

    def get_latest_pointer(
        self,
        *,
        project_id: str,
        artifact_type: str,
    ) -> ProjectArtifactPointer | None:
        """Load pointer for the most recent artifact revision."""

        normalized_project_id = _validate_project_id(project_id)
        normalized_type = _validate_artifact_type(artifact_type)
        with self._session_factory() as session:
            row = (
                session.execute(
                    text(
                        """
                    SELECT * FROM artifacts
                    WHERE project_id = :project_id AND artifact_type = :artifact_type
                    ORDER BY revision_no DESC
                    LIMIT 1
                    """
                    ),
                    {"project_id": normalized_project_id, "artifact_type": normalized_type},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _pointer_from_row(dict(row))

    def read_latest_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
    ) -> ProjectArtifactDocument | None:
        """Load pointer and full content for the most recent artifact revision."""

        normalized_project_id = _validate_project_id(project_id)
        normalized_type = _validate_artifact_type(artifact_type)
        with self._session_factory() as session:
            row = (
                session.execute(
                    text(
                        """
                    SELECT * FROM artifacts
                    WHERE project_id = :project_id AND artifact_type = :artifact_type
                    ORDER BY revision_no DESC
                    LIMIT 1
                    """
                    ),
                    {"project_id": normalized_project_id, "artifact_type": normalized_type},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        row_dict = dict(row)
        return ProjectArtifactDocument(
            pointer=_pointer_from_row(row_dict),
            content=str(row_dict.get("content", "")),
        )

    def list_pointers(
        self,
        *,
        project_id: str,
        artifact_type: str,
    ) -> tuple[ProjectArtifactPointer, ...]:
        """List all revision pointers for a project/artifact type, oldest first."""

        normalized_project_id = _validate_project_id(project_id)
        normalized_type = _validate_artifact_type(artifact_type)
        with self._session_factory() as session:
            rows = (
                session.execute(
                    text(
                        """
                    SELECT * FROM artifacts
                    WHERE project_id = :project_id AND artifact_type = :artifact_type
                    ORDER BY revision_no ASC
                    """
                    ),
                    {"project_id": normalized_project_id, "artifact_type": normalized_type},
                )
                .mappings()
                .all()
            )
        return tuple(_pointer_from_row(dict(row)) for row in rows)


# ---------------------------------------------------------------------------
# Authorization helpers (duplicated from InMemoryProjectArtifactRepository)
# ---------------------------------------------------------------------------


def _assert_write_authorization(
    *,
    artifact_type: str,
    write_context: ProjectArtifactWriteContext,
) -> None:
    actor_role = write_context.actor_role.strip().lower()
    project_status = write_context.project_status.strip().lower()

    if project_status not in _PROJECT_WRITABLE_STATES:
        raise ProjectArtifactRepositoryError(
            code="artifact_project_not_writable",
            message=f"project status does not allow artifact writes: {project_status}",
        )
    if actor_role == "project_manager":
        if artifact_type in _PROJECT_MANAGER_FORBIDDEN_WRITE_TYPES:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_forbidden",
                message=f"project_manager cannot write artifact type: {artifact_type}",
            )
        return
    if actor_role in {"owner", "ceo", "cwo"}:
        return
    raise ProjectArtifactRepositoryError(
        code="artifact_write_role_forbidden",
        message=f"actor role cannot write artifacts: {actor_role}",
    )


def _assert_total_cap(total_count: int, cap: int) -> None:
    if total_count >= cap:
        raise ProjectArtifactRepositoryError(
            code="artifact_project_document_cap_exceeded",
            message=(f"project total active-document cap exceeded: ({total_count}/{cap})"),
        )


def _validate_project_id(project_id: str) -> str:
    normalized = project_id.strip()
    if not _PROJECT_ID_PATTERN.match(normalized):
        raise ProjectArtifactRepositoryError(
            code="artifact_project_id_invalid",
            message=f"project_id format invalid: {project_id!r}",
        )
    return normalized


def _validate_artifact_type(artifact_type: str) -> str:
    normalized = artifact_type.strip().lower()
    if not _ARTIFACT_TYPE_PATTERN.match(normalized):
        raise ProjectArtifactRepositoryError(
            code="artifact_type_invalid",
            message=f"artifact_type format invalid: {artifact_type!r}",
        )
    return normalized


def _pointer_from_row(row: dict[str, object]) -> ProjectArtifactPointer:
    created_at = row["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at).astimezone(UTC)
    elif hasattr(created_at, "tzinfo") and created_at.tzinfo is None:  # type: ignore[union-attr]
        created_at = created_at.replace(tzinfo=UTC)  # type: ignore[union-attr]
    return ProjectArtifactPointer(
        project_id=str(row["project_id"]),
        artifact_type=str(row["artifact_type"]),
        revision_no=int(row["revision_no"]),  # type: ignore[arg-type]
        storage_uri=str(row["storage_uri"]),
        content_hash=str(row["content_hash"]),
        created_at=created_at,  # type: ignore[arg-type]
        byte_size=int(row["byte_size"]),  # type: ignore[arg-type]
    )
