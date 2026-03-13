from pathlib import Path


def test_m10_wp6_conformance_evidence_pack_exists_and_maps_exit_criteria() -> None:
    project_root = Path(__file__).resolve().parents[2]
    evidence_pack = (
        project_root / "implementation/v1/planning/milestones/m10/M10EvidencePack-v1.md"
    ).read_text(encoding="utf-8")

    for snippet in (
        "## 3. Evidence Map by M10 Exit Checklist",
        "### 3.1 Role-bot identity registry and startup hardening",
        "### 3.2 Multi-bot runtime fan-in and bot-identity ingress context",
        "### 3.3 DM + mention group recipient governance routing",
        "### 3.4 Role lock, injection denial, and memory isolation",
        "### 3.5 Outbound delivery hardening (chunking, retry, ordering)",
        "### 3.6 Live multi-bot acceptance + operator runbook",
        "tests/unit/test_m10_wp1_role_bot_registry.py",
        "tests/component/test_m10_wp2_multi_bot_runtime.py",
        "tests/integration/test_m10_wp3_discord_recipient_routing.py",
        "tests/unit/test_m10_wp5_discord_delivery_hardening.py",
        "tests/conformance/test_m10_wp6_evidence_pack_conformance.py",
        "tests/unit/test_m10_wp6_live_acceptance_artifact_checks.py",
        "ops/scripts/run_m10_live_multi_bot_acceptance.py",
        "ops/scripts/check_m10_live_acceptance_artifacts.py",
        "M10LiveAcceptanceChecklist-v1.md",
        "M10MultiBotOperatorRunbook-v1.md",
    ):
        assert snippet in evidence_pack


def test_m10_wp6_conformance_checklist_and_runbook_exist() -> None:
    project_root = Path(__file__).resolve().parents[2]
    checklist_path = (
        project_root / "implementation/v1/planning/milestones/m10/M10LiveAcceptanceChecklist-v1.md"
    )
    runbook_path = (
        project_root / "implementation/v1/planning/milestones/m10/M10MultiBotOperatorRunbook-v1.md"
    )

    checklist = checklist_path.read_text(encoding="utf-8")
    runbook = runbook_path.read_text(encoding="utf-8")

    for snippet in (
        "### 4.1 Direct Message Matrix",
        "### 4.2 Mention-Driven Group Chat",
        "### 4.3 Long-Response Hardening",
        "m10_live_scenarios_manifest_latest.json",
    ):
        assert snippet in checklist

    for snippet in (
        "OPENQILIN_DISCORD_ROLE_BOT_TOKENS_FILE",
        "OPENQILIN_DISCORD_ROLE_BOT_TOKENS_JSON",
        "OPENQILIN_DISCORD_REQUIRED_ROLE_BOTS_CSV",
        "OPENQILIN_DISCORD_RESPONSE_CHUNK_SIZE_CHARS",
        "Incident Response",
    ):
        assert snippet in runbook
