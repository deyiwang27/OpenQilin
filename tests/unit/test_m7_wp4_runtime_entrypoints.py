import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from openqilin.apps.communication_worker import main as communication_worker_main
from openqilin.apps import communication_worker as communication_worker_module
from openqilin.apps import orchestrator_worker as orchestrator_worker_module
from openqilin.apps.orchestrator_worker import main as orchestrator_worker_main
from openqilin.control_plane.api.app import create_control_plane_app


def test_m7_wp4_api_exposes_container_health_endpoints() -> None:
    with patch(
        "openqilin.control_plane.api.app.build_runtime_services",
        return_value=MagicMock(),
    ):
        app = create_control_plane_app()
    client = TestClient(app)

    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "live"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_m7_wp4_orchestrator_worker_run_once_emits_ready_marker(
    monkeypatch, tmp_path: Path
) -> None:
    marker = tmp_path / "orchestrator.ready"
    monkeypatch.setattr(orchestrator_worker_module, "READY_MARKER_PATH", marker)

    asyncio.run(orchestrator_worker_main(run_once=True))

    assert marker.exists()


def test_m7_wp4_communication_worker_run_once_emits_ready_marker(
    monkeypatch, tmp_path: Path
) -> None:
    marker = tmp_path / "communication.ready"
    monkeypatch.setattr(communication_worker_module, "READY_MARKER_PATH", marker)

    asyncio.run(communication_worker_main(run_once=True))

    assert marker.exists()
