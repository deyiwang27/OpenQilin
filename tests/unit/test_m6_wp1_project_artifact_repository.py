from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from openqilin.data_access.repositories.artifacts import (
    InMemoryProjectArtifactRepository,
    ProjectArtifactRepositoryError,
    ProjectArtifactWriteContext,
)


def _cwo_context() -> ProjectArtifactWriteContext:
    return ProjectArtifactWriteContext(
        actor_role="cwo",
        project_status="approved",
        approval_roles=("ceo", "cwo"),
    )


def test_write_project_artifact_persists_canonical_path_and_hash(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    pointer = repository.write_project_artifact(
        project_id="project_m6_wp1",
        artifact_type="project_charter",
        content="# Charter\n\nM6 WP1 content",
        write_context=_cwo_context(),
    )

    expected_path = (
        tmp_path
        / "system_root"
        / "projects"
        / "project_m6_wp1"
        / "docs"
        / "project_charter"
        / "project_charter--v001.md"
    )
    assert Path(pointer.storage_uri) == expected_path
    assert (
        pointer.content_hash
        == hashlib.sha256("# Charter\n\nM6 WP1 content".encode("utf-8")).hexdigest()
    )
    assert repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="project_charter",
    )
    document = repository.read_latest_artifact(
        project_id="project_m6_wp1",
        artifact_type="project_charter",
    )
    assert document is not None
    assert document.content == "# Charter\n\nM6 WP1 content"
    assert document.pointer.revision_no == 1


def test_write_project_artifact_increments_revision_per_type(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    first = repository.write_project_artifact(
        project_id="project_m6_wp1",
        artifact_type="project_charter",
        content="v1",
        write_context=_cwo_context(),
    )
    second = repository.write_project_artifact(
        project_id="project_m6_wp1",
        artifact_type="project_charter",
        content="v2",
        write_context=_cwo_context(),
    )

    assert first.revision_no == 1
    assert second.revision_no == 2
    assert second.storage_uri.endswith("project_charter--v002.md")


def test_verify_pointer_hash_detects_tampered_file(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")
    pointer = repository.write_project_artifact(
        project_id="project_m6_wp1",
        artifact_type="success_metrics",
        content="delivery: green",
        write_context=_cwo_context(),
    )

    Path(pointer.storage_uri).write_text("tampered", encoding="utf-8")

    assert not repository.verify_pointer_hash(
        project_id="project_m6_wp1",
        artifact_type="success_metrics",
    )


@pytest.mark.parametrize(
    ("project_id", "artifact_type", "expected_code"),
    (
        ("../escape", "project_charter", "artifact_project_id_invalid"),
        ("project_m6_wp1", "../escape", "artifact_type_invalid"),
    ),
)
def test_write_project_artifact_rejects_invalid_identifiers(
    tmp_path: Path,
    project_id: str,
    artifact_type: str,
    expected_code: str,
) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")
    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
            content="x",
            write_context=_cwo_context(),
        )

    assert exc.value.code == expected_code


def test_write_project_artifact_rejects_missing_write_context(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp1",
            artifact_type="project_charter",
            content="x",
        )

    assert exc.value.code == "artifact_write_context_missing"
