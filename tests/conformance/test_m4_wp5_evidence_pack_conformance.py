from pathlib import Path


def test_m4_wp5_conformance_evidence_pack_exists_and_maps_exit_criteria() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (project_root / "implementation/v1/planning/M4EvidencePack-v1.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "## 3. Evidence Map by M4 Exit Checklist",
        "### 3.1 Release-readiness dashboards and alerts are defined, runbook-linked, and validated",
        "### 3.2 Migration and rollback drills are repeatable with recorded evidence",
        "### 3.3 `full` profile smoke and conformance gates are deterministic promotion blockers",
        "### 3.4 Release artifact and promotion checklist package is complete and operator-usable",
        "### 3.5 Full quality and release gates pass for merged M4 scope",
        "tests/unit/test_m4_wp1_observability_release_readiness.py",
        "tests/unit/test_m4_wp2_migration_rollback_drill.py",
        "tests/conformance/test_m4_wp3_release_gate_hardening_conformance.py",
        "tests/conformance/test_m4_wp4_release_artifact_package_conformance.py",
    ):
        assert snippet in evidence_pack


def test_m4_wp5_conformance_evidence_pack_contains_closeout_workflow_and_links() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (project_root / "implementation/v1/planning/M4EvidencePack-v1.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "Open milestone closeout PR from `feat/21-m4-hardening-release-kickoff` to `main`.",
        "Close parent issue `#21` with merge commit and evidence links.",
        "https://github.com/deyiwang27/OpenQilin/issues/21",
        "https://github.com/deyiwang27/OpenQilin/issues/22",
        "https://github.com/deyiwang27/OpenQilin/issues/23",
        "https://github.com/deyiwang27/OpenQilin/issues/24",
        "https://github.com/deyiwang27/OpenQilin/issues/25",
        "https://github.com/deyiwang27/OpenQilin/issues/26",
    ):
        assert snippet in evidence_pack
