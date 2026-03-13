"""Runtime startup validation guards."""

from __future__ import annotations

from openqilin.discord_runtime.role_bot_registry import (
    RoleBotRegistryError,
    build_role_bot_registry,
)
from openqilin.shared_kernel.config import RuntimeSettings

_LOCAL_ENV_VALUES = frozenset({"local", "local_dev", "development", "test", "ci"})
_UNSAFE_CONNECTOR_SECRETS = frozenset({"", "dev-openqilin-secret"})


def enforce_connector_secret_hardening(settings: RuntimeSettings) -> None:
    """Fail closed for non-local environments with unsafe connector shared secret."""

    normalized_env = settings.env.strip().lower()
    if normalized_env in _LOCAL_ENV_VALUES:
        return
    normalized_secret = settings.connector_shared_secret.strip()
    if normalized_secret in _UNSAFE_CONNECTOR_SECRETS:
        raise RuntimeError(
            "non-local runtime requires non-default OPENQILIN_CONNECTOR_SHARED_SECRET"
        )


def enforce_discord_role_bot_registry(settings: RuntimeSettings) -> None:
    """Fail closed when multi-bot role registry configuration is invalid."""

    if not settings.discord_multi_bot_enabled:
        return
    try:
        build_role_bot_registry(settings)
    except RoleBotRegistryError as error:
        raise RuntimeError(
            f"invalid Discord role-bot registry: {error.code} {error.message}"
        ) from error
