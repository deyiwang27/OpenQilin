from pathlib import Path

from openqilin.release_readiness.artifact_packaging import (
    build_release_artifact_bundle,
    validate_release_artifact_bundle,
)


def test_m4_wp4_conformance_release_docs_have_required_decision_and_traceability_content() -> None:
    project_root = Path(__file__).resolve().parents[2]
    checklist = (
        project_root / "implementation/v1/quality/ReleasePromotionChecklist-v1.md"
    ).read_text(encoding="utf-8")
    artifact_index = (
        project_root / "implementation/v1/planning/ReleaseArtifactIndex-v1.md"
    ).read_text(encoding="utf-8")

    for snippet in (
        "D1_ci_and_quality_gates",
        "D2_release_candidate_gate_matrix",
        "D3_migration_and_rollback_readiness",
        "D4_manual_go_no_go",
        "Rollback Hook",
    ):
        assert snippet in checklist

    for snippet in (
        "compose.yml",
        "implementation/v1/quality/ReleasePromotionChecklist-v1.md",
        "src/openqilin/release_readiness/gate_matrix.py",
    ):
        assert snippet in artifact_index


def test_m4_wp4_conformance_release_artifact_bundle_contract_validates() -> None:
    bundle = build_release_artifact_bundle(
        release_version="0.1.0-rc-template",
        git_commit="deadbee",
        generated_at_utc="2026-03-12T00:00:00+00:00",
    )

    assert validate_release_artifact_bundle(bundle) == []
