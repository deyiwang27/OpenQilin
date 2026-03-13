from pathlib import Path
import re


def _extract_compose_service_block(compose_text: str, service_name: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^  {re.escape(service_name)}:\n(?P<body>(?:    .*\n)+?)(?=^  [a-zA-Z0-9_]+:|\Z)"
    )
    match = pattern.search(compose_text)
    if match is None:
        return None
    return match.group("body")


def test_m7_wp4_conformance_full_profile_runtime_services_use_real_entrypoints() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_text = (project_root / "compose.yml").read_text(encoding="utf-8")

    api_block = _extract_compose_service_block(compose_text, "api_app")
    orchestrator_block = _extract_compose_service_block(compose_text, "orchestrator_worker")
    communication_block = _extract_compose_service_block(compose_text, "communication_worker")

    assert api_block is not None
    assert orchestrator_block is not None
    assert communication_block is not None

    assert 'profiles: ["full"]' in api_block
    assert 'profiles: ["full"]' in orchestrator_block
    assert 'profiles: ["full"]' in communication_block

    assert "placeholder container" not in api_block
    assert "placeholder container" not in orchestrator_block
    assert "placeholder container" not in communication_block

    assert "uvicorn openqilin.apps.api_app:app --host 0.0.0.0 --port 8000" in api_block
    assert "python -m openqilin.apps.orchestrator_worker" in orchestrator_block
    assert "python -m openqilin.apps.communication_worker" in communication_block


def test_m7_wp4_conformance_startup_health_dependencies_are_declared() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_text = (project_root / "compose.yml").read_text(encoding="utf-8")

    api_block = _extract_compose_service_block(compose_text, "api_app")
    orchestrator_block = _extract_compose_service_block(compose_text, "orchestrator_worker")
    communication_block = _extract_compose_service_block(compose_text, "communication_worker")

    assert api_block is not None
    assert orchestrator_block is not None
    assert communication_block is not None

    assert "/health/live" in api_block
    assert "litellm:" in api_block
    assert "condition: service_healthy" in api_block

    assert "api_app:" in orchestrator_block
    assert "condition: service_healthy" in orchestrator_block
    assert "openqilin.orchestrator_worker.ready" in orchestrator_block

    assert "api_app:" in communication_block
    assert "condition: service_healthy" in communication_block
    assert "openqilin.communication_worker.ready" in communication_block
