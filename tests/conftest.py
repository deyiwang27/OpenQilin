"""Root test conftest: clear RuntimeSettings singleton cache before every test.

``get_settings()`` uses ``@lru_cache(maxsize=1)``. Tests that monkeypatch
OPENQILIN_* environment variables need a fresh settings instance — clearing
the cache here ensures every test starts with a clean state.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear the RuntimeSettings singleton cache before each test."""
    from openqilin.shared_kernel.settings import get_settings

    get_settings.cache_clear()
