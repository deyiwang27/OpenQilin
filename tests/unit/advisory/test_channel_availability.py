"""Unit tests for advisory channel restrictions."""

from __future__ import annotations

from openqilin.control_plane.advisory.channel_availability import (
    is_role_available_in_channel,
)


def test_auditor_not_in_project_channel() -> None:
    assert is_role_available_in_channel("auditor", True) is False


def test_administrator_not_in_project_channel() -> None:
    assert is_role_available_in_channel("administrator", True) is False


def test_auditor_in_general_channel() -> None:
    assert is_role_available_in_channel("auditor", False) is True


def test_cso_in_project_channel() -> None:
    assert is_role_available_in_channel("cso", True) is True


def test_secretary_in_project_channel() -> None:
    assert is_role_available_in_channel("secretary", True) is True


def test_ceo_in_project_channel() -> None:
    assert is_role_available_in_channel("ceo", True) is True
