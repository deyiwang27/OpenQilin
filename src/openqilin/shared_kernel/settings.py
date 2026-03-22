"""RuntimeSettings singleton factory.

Production code must call ``get_settings()`` — never construct ``RuntimeSettings()``
directly. Test fixtures may call ``get_settings.cache_clear()`` to reset the cache
between test cases.
"""

import os
from functools import lru_cache
from typing import Protocol, cast

from openqilin.shared_kernel.config import RuntimeSettings


def _resolve_cache_scope() -> str | None:
    """Return cache scope key.

    Production scope is process-wide (None). During pytest runs, scope is one test
    case id so env monkeypatches do not leak across tests.
    """

    pytest_test = os.getenv("PYTEST_CURRENT_TEST")
    if pytest_test is None:
        return None
    normalized = pytest_test.split(" (", 1)[0].strip()
    return normalized or None


@lru_cache(maxsize=1)
def _build_settings(cache_scope: str | None) -> RuntimeSettings:
    """Build cached RuntimeSettings for one cache scope."""

    _ = cache_scope
    return RuntimeSettings()


class SettingsFactory(Protocol):
    """Callable RuntimeSettings factory with cache reset support."""

    def __call__(self) -> RuntimeSettings: ...

    def cache_clear(self) -> None: ...


def _get_settings() -> RuntimeSettings:
    """Return the process-wide RuntimeSettings singleton.

    Reads environment variables exactly once on first call.
    Subsequent calls return the cached instance — zero I/O.
    """

    return _build_settings(_resolve_cache_scope())


def _cache_clear() -> None:
    _build_settings.cache_clear()


setattr(_get_settings, "cache_clear", _cache_clear)
get_settings = cast(SettingsFactory, _get_settings)
