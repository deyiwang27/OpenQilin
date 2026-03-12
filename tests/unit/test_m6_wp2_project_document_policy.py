from __future__ import annotations

from pathlib import Path

import pytest

from openqilin.data_access.repositories.artifacts import (
    InMemoryProjectArtifactRepository,
    ProjectArtifactRepositoryError,
    ProjectDocumentPolicy,
    ProjectArtifactWriteContext,
)


def _cwo_context() -> ProjectArtifactWriteContext:
    return ProjectArtifactWriteContext(
        actor_role="cwo",
        project_status="approved",
        approval_roles=("ceo", "cwo"),
    )


def test_write_project_artifact_rejects_out_of_policy_type(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="custom_notes",
            content="not allowed",
            write_context=_cwo_context(),
        )

    assert exc.value.code == "artifact_type_not_allowed"


def test_write_project_artifact_enforces_per_type_cap(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(
        system_root=tmp_path / "system_root",
        policy=ProjectDocumentPolicy(
            allowed_type_caps={"progress_report": 3},
            total_active_document_cap=10,
        ),
    )

    first = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="progress_report",
        content="progress 1",
        write_context=_cwo_context(),
    )
    second = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="progress_report",
        content="progress 2",
        write_context=_cwo_context(),
    )
    third = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="progress_report",
        content="progress 3",
        write_context=_cwo_context(),
    )
    assert (first.revision_no, second.revision_no, third.revision_no) == (1, 2, 3)

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="progress_report",
            content="progress 4",
            write_context=_cwo_context(),
        )

    assert exc.value.code == "artifact_type_cap_exceeded"


def test_write_project_artifact_enforces_total_cap(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(
        system_root=tmp_path / "system_root",
        policy=ProjectDocumentPolicy(
            allowed_type_caps={"project_charter": 1, "progress_report": 3},
            total_active_document_cap=2,
        ),
    )
    repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="project_charter",
        content="charter",
        write_context=_cwo_context(),
    )
    repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="progress_report",
        content="progress 1",
        write_context=_cwo_context(),
    )

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="progress_report",
            content="progress 2",
            write_context=_cwo_context(),
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
        write_context=_cwo_context(),
    )
    second = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="project_charter",
        content="v2",
        write_context=_cwo_context(),
    )
    third = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="risk_register",
        content="risk 1",
        write_context=_cwo_context(),
    )

    assert first.revision_no == 1
    assert second.revision_no == 2
    assert third.revision_no == 1


def test_project_manager_write_requires_active_state(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="execution_plan",
            content="plan",
            write_context=ProjectArtifactWriteContext(
                actor_role="project_manager",
                project_status="paused",
                approval_roles=(),
            ),
        )

    assert exc.value.code == "artifact_write_project_manager_inactive"


def test_project_manager_controlled_write_requires_ceo_cwo_approval(tmp_path: Path) -> None:
    repository = InMemoryProjectArtifactRepository(system_root=tmp_path / "system_root")

    with pytest.raises(ProjectArtifactRepositoryError) as exc:
        repository.write_project_artifact(
            project_id="project_m6_wp2",
            artifact_type="success_metrics",
            content="metric update",
            write_context=ProjectArtifactWriteContext(
                actor_role="project_manager",
                project_status="active",
                approval_roles=("cwo",),
            ),
        )

    assert exc.value.code == "artifact_write_project_manager_approval_missing"

    pointer = repository.write_project_artifact(
        project_id="project_m6_wp2",
        artifact_type="success_metrics",
        content="metric update approved",
        write_context=ProjectArtifactWriteContext(
            actor_role="project_manager",
            project_status="active",
            approval_roles=("ceo", "cwo"),
        ),
    )
    assert pointer.revision_no == 1
