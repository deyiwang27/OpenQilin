"""Project artifact repository with canonical file-root and pointer/hash contracts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from openqilin.shared_kernel.config import RuntimeSettings

_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ARTIFACT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


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


class InMemoryProjectArtifactRepository:
    """File-backed project artifact repository with in-memory pointer index."""

    def __init__(self, *, system_root: Path | None = None) -> None:
        configured_root = system_root or RuntimeSettings().system_root_path
        root = Path(configured_root).expanduser()
        if not str(root).strip():
            raise ProjectArtifactRepositoryError(
                code="artifact_system_root_invalid",
                message="OPENQILIN_SYSTEM_ROOT must be configured",
            )
        self._system_root = root.resolve()
        self._latest_by_key: dict[tuple[str, str], ProjectArtifactPointer] = {}
        self._history_by_key: dict[tuple[str, str], tuple[ProjectArtifactPointer, ...]] = {}

    @property
    def system_root(self) -> Path:
        """Canonical system root used for project documentation."""

        return self._system_root

    def write_project_artifact(
        self,
        *,
        project_id: str,
        artifact_type: str,
        content: str,
    ) -> ProjectArtifactPointer:
        """Persist one artifact revision and return pointer/hash metadata."""

        normalized_project_id = self._validate_project_id(project_id)
        normalized_type = self._validate_artifact_type(artifact_type)
        key = (normalized_project_id, normalized_type)

        latest = self._latest_by_key.get(key)
        revision_no = 1 if latest is None else latest.revision_no + 1

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

    def _assert_under_system_root(self, path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(self._system_root)
        except ValueError as error:
            raise ProjectArtifactRepositoryError(
                code="artifact_path_outside_system_root",
                message=f"path escapes OPENQILIN_SYSTEM_ROOT: {resolved}",
            ) from error
