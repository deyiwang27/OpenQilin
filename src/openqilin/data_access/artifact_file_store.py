"""File-backed storage for project artifacts.

Writes artifact content to the canonical path under OPENQILIN_SYSTEM_ROOT and
returns (storage_uri, content_hash) for DB storage. Never writes inside the
source repository tree.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class ArtifactFileStoreError(Exception):
    """Raised when ArtifactFileStore contract checks fail."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ArtifactFileStore:
    """Canonical file-backed storage for project artifact content."""

    def __init__(self, system_root: Path) -> None:
        self._system_root = system_root
        self._projects_root = system_root / "projects"

    def write(
        self,
        *,
        project_id: str,
        artifact_type: str,
        version_no: int,
        content_md: str,
    ) -> tuple[str, str]:
        """Write artifact content to canonical path."""

        path = self._canonical_path(project_id, artifact_type, version_no)
        self._assert_within_projects_root(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content_md, encoding="utf-8")
        except OSError as exc:
            raise ArtifactFileStoreError(
                code="artifact_file_store_write_error",
                message=str(exc),
            ) from exc

        content_hash = self.compute_hash(content_md)
        storage_uri = f"file://{path.resolve()}"
        return storage_uri, content_hash

    def read(self, storage_uri: str) -> str:
        """Read artifact content from a file:// storage_uri."""

        if not storage_uri.startswith("file://"):
            raise ArtifactFileStoreError(
                code="artifact_file_store_scheme_invalid",
                message=f"storage_uri must start with file://, got: {storage_uri!r}",
            )
        path = Path(storage_uri[len("file://") :])
        self._assert_within_projects_root(path)
        if not path.exists():
            raise ArtifactFileStoreError(
                code="artifact_file_store_not_found",
                message=f"artifact file not found: {path}",
            )
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ArtifactFileStoreError(
                code="artifact_file_store_read_error",
                message=str(exc),
            ) from exc

    def compute_hash(self, content: str) -> str:
        """Return sha256 hex digest of content encoded as UTF-8."""

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _canonical_path(
        self,
        project_id: str,
        artifact_type: str,
        version_no: int,
    ) -> Path:
        return self._projects_root / project_id / f"{artifact_type}-v{version_no:03d}.md"

    def _assert_within_projects_root(self, path: Path) -> None:
        resolved = path.resolve()
        projects_root_resolved = self._projects_root.resolve()
        try:
            resolved.relative_to(projects_root_resolved)
        except ValueError as exc:
            raise ArtifactFileStoreError(
                code="artifact_file_store_path_traversal",
                message=f"path escapes projects root: {resolved}",
            ) from exc
