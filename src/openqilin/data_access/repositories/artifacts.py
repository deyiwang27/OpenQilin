"""Project artifact repository with canonical file-root and pointer/hash contracts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from openqilin.shared_kernel.config import RuntimeSettings

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
    }
)
_MVP_PROJECT_TOTAL_ACTIVE_DOCUMENT_CAP = 20
_APPEND_ONLY_ARTIFACT_TYPES = frozenset(
    {
        "decision_log",
        "progress_report",
        "completion_report",
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


class InMemoryProjectArtifactRepository:
    """File-backed project artifact repository with in-memory pointer index."""

    def __init__(
        self,
        *,
        system_root: Path | None = None,
        policy: ProjectDocumentPolicy | None = None,
    ) -> None:
        configured_root = system_root or RuntimeSettings().system_root_path
        root = Path(configured_root).expanduser()
        if not str(root).strip():
            raise ProjectArtifactRepositoryError(
                code="artifact_system_root_invalid",
                message="OPENQILIN_SYSTEM_ROOT must be configured",
            )
        self._system_root = root.resolve()
        self._policy = policy or ProjectDocumentPolicy.mvp_defaults()
        self._latest_by_key: dict[tuple[str, str], ProjectArtifactPointer] = {}
        self._history_by_key: dict[tuple[str, str], tuple[ProjectArtifactPointer, ...]] = {}
        self._active_doc_count_by_key: dict[tuple[str, str], int] = {}
        self._total_active_doc_count_by_project: dict[str, int] = {}

    @property
    def system_root(self) -> Path:
        """Canonical system root used for project documentation."""

        return self._system_root

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

        normalized_project_id = self._validate_project_id(project_id)
        normalized_type = self._validate_artifact_type(artifact_type)
        self._assert_write_authorization(artifact_type=normalized_type, write_context=write_context)
        key = (normalized_project_id, normalized_type)
        per_type_cap = self._policy.cap_for_type(normalized_type)
        latest = self._latest_by_key.get(key)
        is_append_only = normalized_type in _APPEND_ONLY_ARTIFACT_TYPES

        if is_append_only:
            active_count = self._active_doc_count_by_key.get(key, 0)
            if active_count >= per_type_cap:
                raise ProjectArtifactRepositoryError(
                    code="artifact_type_cap_exceeded",
                    message=(
                        "artifact_type active-document cap exceeded: "
                        f"{normalized_type} ({active_count}/{per_type_cap})"
                    ),
                )
            self._assert_total_document_cap_available(project_id=normalized_project_id)
            revision_no = active_count + 1
        else:
            revision_no = 1 if latest is None else latest.revision_no + 1
            if latest is None:
                self._assert_total_document_cap_available(project_id=normalized_project_id)

        payload = content.encode("utf-8")
        content_hash = hashlib.sha256(payload).hexdigest()

        artifact_dir = self._project_docs_root(normalized_project_id) / normalized_type
        target_path = artifact_dir / f"{normalized_type}--v{revision_no:03d}.md"
        self._assert_under_system_root(target_path)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload)

        pointer = ProjectArtifactPointer(
            project_id=normalized_project_id,
            artifact_type=normalized_type,
            revision_no=revision_no,
            storage_uri=str(target_path),
            content_hash=content_hash,
            created_at=datetime.now(tz=UTC),
            byte_size=len(payload),
        )
        history = self._history_by_key.get(key, ())
        self._history_by_key[key] = history + (pointer,)
        self._latest_by_key[key] = pointer
        if is_append_only:
            self._register_new_active_document(project_id=normalized_project_id, key=key)
        elif latest is None:
            self._register_new_active_document(project_id=normalized_project_id, key=key)
        return pointer

    def get_latest_pointer(
        self, *, project_id: str, artifact_type: str
    ) -> ProjectArtifactPointer | None:
        """Return latest pointer for one project artifact type."""

        key = (self._validate_project_id(project_id), self._validate_artifact_type(artifact_type))
        return self._latest_by_key.get(key)

    def list_latest_pointers(self, *, project_id: str) -> tuple[ProjectArtifactPointer, ...]:
        """Return latest pointers for all artifact types in one project."""

        normalized_project_id = self._validate_project_id(project_id)
        pointers = [
            pointer
            for (candidate_project_id, _), pointer in self._latest_by_key.items()
            if candidate_project_id == normalized_project_id
        ]
        return tuple(sorted(pointers, key=lambda pointer: pointer.artifact_type))

    def read_latest_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
    ) -> ProjectArtifactDocument | None:
        """Read latest artifact content and pointer metadata."""

        pointer = self.get_latest_pointer(project_id=project_id, artifact_type=artifact_type)
        if pointer is None:
            return None
        path = Path(pointer.storage_uri)
        self._assert_under_system_root(path)
        if not path.exists():
            raise ProjectArtifactRepositoryError(
                code="artifact_file_missing",
                message=f"artifact file missing: {pointer.storage_uri}",
            )
        content = path.read_text(encoding="utf-8")
        return ProjectArtifactDocument(pointer=pointer, content=content)

    def verify_pointer_hash(
        self,
        *,
        project_id: str,
        artifact_type: str,
    ) -> bool:
        """Verify latest pointer hash against file-backed bytes."""

        pointer = self.get_latest_pointer(project_id=project_id, artifact_type=artifact_type)
        if pointer is None:
            raise ProjectArtifactRepositoryError(
                code="artifact_pointer_missing",
                message="artifact pointer not found",
            )
        path = Path(pointer.storage_uri)
        self._assert_under_system_root(path)
        if not path.exists():
            raise ProjectArtifactRepositoryError(
                code="artifact_file_missing",
                message=f"artifact file missing: {pointer.storage_uri}",
            )
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        return current_hash == pointer.content_hash

    def _project_docs_root(self, project_id: str) -> Path:
        return self._system_root / "projects" / project_id / "docs"

    @staticmethod
    def _validate_project_id(project_id: str) -> str:
        normalized = project_id.strip()
        if not _PROJECT_ID_PATTERN.fullmatch(normalized):
            raise ProjectArtifactRepositoryError(
                code="artifact_project_id_invalid",
                message=f"invalid project_id: {project_id}",
            )
        return normalized

    @staticmethod
    def _validate_artifact_type(artifact_type: str) -> str:
        normalized = artifact_type.strip().lower()
        if not _ARTIFACT_TYPE_PATTERN.fullmatch(normalized):
            raise ProjectArtifactRepositoryError(
                code="artifact_type_invalid",
                message=f"invalid artifact_type: {artifact_type}",
            )
        return normalized

    def _assert_total_document_cap_available(self, *, project_id: str) -> None:
        current_total = self._total_active_doc_count_by_project.get(project_id, 0)
        if current_total >= self._policy.total_active_document_cap:
            raise ProjectArtifactRepositoryError(
                code="artifact_project_total_cap_exceeded",
                message=(
                    "project total active-document cap exceeded: "
                    f"{current_total}/{self._policy.total_active_document_cap}"
                ),
            )

    def _register_new_active_document(self, *, project_id: str, key: tuple[str, str]) -> None:
        self._active_doc_count_by_key[key] = self._active_doc_count_by_key.get(key, 0) + 1
        self._total_active_doc_count_by_project[project_id] = (
            self._total_active_doc_count_by_project.get(project_id, 0) + 1
        )

    @staticmethod
    def _assert_write_authorization(
        *,
        artifact_type: str,
        write_context: ProjectArtifactWriteContext,
    ) -> None:
        actor_role = write_context.actor_role.strip().lower()
        project_status = write_context.project_status.strip().lower()
        approval_roles = {
            role.strip().lower() for role in write_context.approval_roles if role.strip()
        }

        if project_status not in _PROJECT_WRITABLE_STATES:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_project_read_only",
                message=f"project status is read-only for document writes: {project_status}",
            )

        if actor_role in {"owner", "ceo", "cwo"}:
            return

        if actor_role != "project_manager":
            raise ProjectArtifactRepositoryError(
                code="artifact_write_role_forbidden",
                message=f"artifact write forbidden for role: {actor_role}",
            )

        if project_status != "active":
            raise ProjectArtifactRepositoryError(
                code="artifact_write_project_manager_inactive",
                message="project_manager document writes require active project status",
            )

        if artifact_type in _PROJECT_MANAGER_FORBIDDEN_WRITE_TYPES:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_project_manager_forbidden_type",
                message=f"project_manager cannot write artifact_type: {artifact_type}",
            )

        if artifact_type in _PROJECT_MANAGER_CONTROLLED_WRITE_TYPES:
            if {"ceo", "cwo"}.issubset(approval_roles):
                return
            raise ProjectArtifactRepositoryError(
                code="artifact_write_project_manager_approval_missing",
                message=("project_manager controlled document write requires ceo and cwo approval"),
            )

        if artifact_type not in _PROJECT_MANAGER_DIRECT_WRITE_TYPES:
            raise ProjectArtifactRepositoryError(
                code="artifact_write_project_manager_forbidden_type",
                message=f"project_manager cannot write artifact_type: {artifact_type}",
            )

    def _assert_under_system_root(self, path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(self._system_root)
        except ValueError as error:
            raise ProjectArtifactRepositoryError(
                code="artifact_path_outside_system_root",
                message=f"path escapes OPENQILIN_SYSTEM_ROOT: {resolved}",
            ) from error
