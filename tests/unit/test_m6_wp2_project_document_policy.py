from __future__ import annotations

from pathlib import Path

import pytest

from openqilin.data_access.repositories.artifacts import (
    InMemoryProjectArtifactRepository,
    ProjectArtifactRepositoryError,
    ProjectDocumentPolicy,
)


def test_write_project_artifact_rejects_out_of_policy_type(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="custom_notes",
            content="not allowed",
        )

    assert exc.value.code == "artifact_type_not_allowed"


def test_write_project_artifact_enforces_per_type_cap(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    first = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="risk_register",
        content="risk 1",
    )
    second = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="risk_register",
        content="risk 2",
    )
    third = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="risk_register",
        content="risk 3",
    )

    assert (first.revision_no, second.revision_no, third.revision_no) == (1, 2, 3)

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="risk_register",
            content="risk 4",
        )

    assert exc.value.code == "artifact_type_cap_exceeded"


def test_write_project_artifact_enforces_total_cap(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(
        system_root=tmp_path / "system_root",
        policy=ProjectDocumentPolicy(
            allowed_type_caps={"project_charter": 1, "risk_register": 3},
            total_active_document_cap=2,
        ),
    )
    repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="project_charter",
        content="charter",
    )
    repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="risk_register",
        content="risk 1",
    )

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="risk_register",
            content="risk 2",
        )

    assert exc.value.code == "artifact_project_total_cap_exceeded"


def test_singleton_version_update_does_not_consume_additional_total_cap(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(
        system_root=tmp_path / "system_root",
        policy=ProjectDocumentPolicy(
            allowed_type_caps={"project_charter": 1, "risk_register": 3},
            total_active_document_cap=2,
        ),
    )
    first = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="project_charter",
        content="v1",
    )
    second = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="project_charter",
        content="v2",
    )
    third = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="risk_register",
        content="risk 1",
    )

    assert first.revision_no == 1
    assert second.revision_no == 2
    assert third.revision_no == 1
