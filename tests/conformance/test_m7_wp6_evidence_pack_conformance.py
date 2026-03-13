from pathlib import Path


def test_m7_wp6_conformance_evidence_pack_exists_and_maps_exit_criteria() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (project_root / "implementation/v1/planning/M7EvidencePack-v1.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "## 3. Acceptance Matrix by M7 Exit Checklist",
        "### 3.1 Restart/recovery preserves governance and idempotency invariants and restores institutional agents",
        "### 3.2 Discord-origin ingress is governed by fixed chat classes and identity/channel mapping policy",
        "### 3.3 Docker `full` profile runs real runtime entrypoints with startup health dependencies",
        "### 3.4 Gemini Flash free-tier provider path executes with quota telemetry and fail-closed behavior",
        "### 3.5 Full project lifecycle acceptance is validated, including completion and termination branches",
        "tests/unit/test_m7_wp1_runtime_recovery.py",
        "tests/component/test_m7_wp2_wp3_discord_governance_router.py",
        "tests/conformance/test_m7_wp4_runtime_cutover_conformance.py",
        "tests/unit/test_m7_wp5_gemini_provider_path.py",
        "tests/integration/test_m7_wp6_mvp_acceptance_path.py",
    ):
        assert snippet in evidence_pack


def test_m7_wp6_conformance_evidence_pack_contains_closeout_workflow_and_issue_links() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (project_root / "implementation/v1/planning/M7EvidencePack-v1.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "Open milestone closeout PR from `feat/41-m7-persistence-adapter-acceptance-kickoff` to `main`.",
        "Close parent issue `#41` with merge commit and evidence links.",
        "https://github.com/deyiwang27/OpenQilin/issues/41",
        "https://github.com/deyiwang27/OpenQilin/issues/42",
        "https://github.com/deyiwang27/OpenQilin/issues/43",
        "https://github.com/deyiwang27/OpenQilin/issues/44",
        "https://github.com/deyiwang27/OpenQilin/issues/45",
        "https://github.com/deyiwang27/OpenQilin/issues/46",
        "https://github.com/deyiwang27/OpenQilin/issues/47",
    ):
        assert snippet in evidence_pack
