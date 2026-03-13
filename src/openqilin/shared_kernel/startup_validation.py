"""Runtime startup validation guards."""

from __future__ import annotations

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
