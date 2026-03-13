from __future__ import annotations

import asyncio

import pytest

from openqilin.apps.discord_bot_worker import main as discord_worker_main
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.startup_validation import enforce_connector_secret_hardening


def test_m9_wp2_startup_validation_allows_local_default_secret() -> None:
    settings = RuntimeSettings(
        env="local_dev",
        connector_shared_secret="dev-openqilin-secret",
    )
    enforce_connector_secret_hardening(settings)


def test_m9_wp2_startup_validation_rejects_non_local_default_secret() -> None:
    settings = RuntimeSettings(
        env="production",
        connector_shared_secret="dev-openqilin-secret",
    )
    with pytest.raises(RuntimeError) as error:
        enforce_connector_secret_hardening(settings)
    assert "non-local runtime requires non-default" in str(error.value)


def test_m9_wp2_startup_validation_allows_non_local_custom_secret() -> None:
    settings = RuntimeSettings(
        env="production",
        connector_shared_secret="prod-secret-123",
    )
    enforce_connector_secret_hardening(settings)


def test_m9_wp2_control_plane_app_fails_closed_for_non_local_default_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENQILIN_ENV", "production")
    monkeypatch.setenv("OPENQILIN_CONNECTOR_SHARED_SECRET", "dev-openqilin-secret")
    with pytest.raises(RuntimeError) as error:
        create_control_plane_app()
    assert "non-local runtime requires non-default" in str(error.value)


def test_m9_wp2_discord_worker_run_once_fails_closed_for_non_local_default_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENQILIN_ENV", "production")
    monkeypatch.setenv("OPENQILIN_CONNECTOR_SHARED_SECRET", "dev-openqilin-secret")
    with pytest.raises(RuntimeError) as error:
        asyncio.run(discord_worker_main(run_once=True))
    assert "non-local runtime requires non-default" in str(error.value)
