from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openqilin.project_spaces.binding_service import _slugify_channel_name
from openqilin.project_spaces.discord_automator import DiscordChannelAutomator, DiscordChannelError


def _mock_httpx_client(*, status_code: int, body: dict[str, str]) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = body
    response.text = str(body)

    client = MagicMock()
    client.post.return_value = response

    manager = MagicMock()
    manager.__enter__.return_value = client
    manager.__exit__.return_value = None
    return manager


def test_create_channel_success() -> None:
    """DiscordChannelAutomator.create_channel returns channel_id on 201 response."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(status_code=201, body={"id": "123456789"})

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ) as client_ctor:
        channel_id = automator.create_channel(
            "project-123", "guild-123", channel_name="project-website-redesign"
        )

    assert channel_id == "123456789"
    client_ctor.assert_called_once_with(timeout=10.0)


def test_create_channel_200_also_accepted() -> None:
    """200 is also a success status (some Discord API versions return 200)."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(status_code=200, body={"id": "987654321"})

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        channel_id = automator.create_channel(
            "project-200", "guild-200", channel_name="project-ops"
        )

    assert channel_id == "987654321"


def test_create_channel_raises_on_403() -> None:
    """DiscordChannelError raised when Discord returns 403 (missing permission)."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(status_code=403, body={"message": "Missing Permissions"})

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        with pytest.raises(DiscordChannelError):
            automator.create_channel("project-403", "guild-403", channel_name="project-locked")


def test_create_channel_raises_on_404() -> None:
    """DiscordChannelError raised when guild_id is invalid (404)."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(status_code=404, body={"message": "Unknown Guild"})

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        with pytest.raises(DiscordChannelError):
            automator.create_channel("project-404", "guild-missing", channel_name="project-missing")


def test_slugify_channel_name_basic() -> None:
    """'Website Redesign' → 'project-website-redesign'."""

    assert _slugify_channel_name("Website Redesign") == "project-website-redesign"


def test_slugify_channel_name_special_chars() -> None:
    """Special characters stripped; hyphens normalised."""

    assert (
        _slugify_channel_name("  My !!! Project___Name (2026)  ") == "project-my-project-name-2026"
    )


def test_slugify_channel_name_max_length() -> None:
    """Names truncated to 100 chars."""

    value = _slugify_channel_name("x" * 300)
    assert value.startswith("project-")
    assert len(value) == 100
