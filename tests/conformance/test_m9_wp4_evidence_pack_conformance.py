from pathlib import Path


def test_m9_wp4_conformance_evidence_pack_exists_and_maps_exit_criteria() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (project_root / "implementation/v1/planning/M9EvidencePack-v1.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "## 3. Evidence Map by M9 Exit Checklist",
        "### 3.1 Real Discord bot runtime is active and governed",
        "### 3.2 Docker `full` profile includes Discord worker and startup secret hardening",
        "### 3.3 Live Discord acceptance scenarios are executable with deterministic artifact outputs",
        "### 3.4 Live-run execution status and current blocker evidence",
        "tests/unit/test_m9_wp1_discord_bridge.py",
        "tests/conformance/test_m9_wp2_discord_runtime_conformance.py",
        "tests/unit/test_m9_wp3_live_acceptance_script.py",
        "m9_live_preflight_latest.json",
    ):
        assert snippet in evidence_pack


def test_m9_wp4_conformance_evidence_pack_contains_closeout_workflow_and_links() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (project_root / "implementation/v1/planning/M9EvidencePack-v1.md").read_text(
        encoding="utf-8"
    )

    for snippet in (
        "Open milestone closeout PR from `feat/49-m9-real-discord-runtime-kickoff` to `main`.",
        "Close parent issue `#49` with merge commit and evidence links.",
        "https://github.com/deyiwang27/OpenQilin/issues/49",
        "https://github.com/deyiwang27/OpenQilin/issues/53",
        "https://github.com/deyiwang27/OpenQilin/issues/54",
        "https://github.com/deyiwang27/OpenQilin/issues/55",
        "https://github.com/deyiwang27/OpenQilin/issues/56",
    ):
        assert snippet in evidence_pack
