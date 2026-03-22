"""Unit tests for M16-WP1 RuntimeSettings singleton factory."""

import pytest

from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.settings import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_settings_returns_runtime_settings_instance() -> None:
    """Factory returns RuntimeSettings instance."""

    assert isinstance(get_settings(), RuntimeSettings)


def test_get_settings_singleton_identity() -> None:
    """Factory returns same object instance across repeated calls."""

    assert get_settings() is get_settings()


def test_get_settings_cache_clear_creates_new_instance() -> None:
    """Clearing cache forces a new RuntimeSettings instance."""

    first = get_settings()
    get_settings.cache_clear()
    second = get_settings()
    assert second is not first


def test_get_settings_has_expected_defaults() -> None:
    """Factory preserves RuntimeSettings default values."""

    assert get_settings().env == "local_dev"
