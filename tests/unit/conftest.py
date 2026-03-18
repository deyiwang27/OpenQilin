"""Unit-test conftest: auto-apply ``no_infra`` marker to pure-logic tests.

Tests that require the compose stack (DB / Redis / OPA) are in files listed
in ``_INFRA_REQUIRED_FILES``.  All other unit tests are automatically marked
``no_infra`` so they can be selected with ``pytest -m no_infra tests/unit/``.
"""

from __future__ import annotations

import pytest

# Test files in tests/unit/ that call into production code requiring
# a live database, Redis, or OPA.  These tests are NOT tagged no_infra.
_INFRA_REQUIRED_FILES = frozenset(
    {
        "test_m1_wp7_admin_cli.py",
    }
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        file_name = item.path.name if item.path is not None else ""
        if file_name not in _INFRA_REQUIRED_FILES:
            item.add_marker(pytest.mark.no_infra)
