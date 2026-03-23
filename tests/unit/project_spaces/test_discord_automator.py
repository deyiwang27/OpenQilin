from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openqilin.project_spaces.binding_service import _slugify_channel_name
from openqilin.project_spaces.discord_automator import DiscordChannelAutomator, DiscordChannelError


def _mock_response(*, status_code: int, body: dict[str, str] | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = body or {}
    response.text = str(body or {})
    return response


def _mock_httpx_client(
    *,
    post_status_code: int | None = None,
    post_body: dict[str, str] | None = None,
    patch_status_code: int | None = None,
    patch_body: dict[str, str] | None = None,
    put_status_code: int | None = None,
    put_body: dict[str, str] | None = None,
) -> MagicMock:
    client = MagicMock()
    if post_status_code is not None:
        client.post.return_value = _mock_response(status_code=post_status_code, body=post_body)
    if patch_status_code is not None:
        client.patch.return_value = _mock_response(status_code=patch_status_code, body=patch_body)
    if put_status_code is not None:
        client.put.return_value = _mock_response(status_code=put_status_code, body=put_body)

    manager = MagicMock()
    manager.__enter__.return_value = client
    manager.__exit__.return_value = None
    return manager


def test_create_channel_success() -> None:
    """DiscordChannelAutomator.create_channel returns channel_id on 201 response."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(post_status_code=201, post_body={"id": "123456789"})

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
    client_manager = _mock_httpx_client(post_status_code=200, post_body={"id": "987654321"})

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
    client_manager = _mock_httpx_client(
        post_status_code=403,
        post_body={"message": "Missing Permissions"},
    )

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        with pytest.raises(DiscordChannelError):
            automator.create_channel("project-403", "guild-403", channel_name="project-locked")


def test_create_channel_raises_on_404() -> None:
    """DiscordChannelError raised when guild_id is invalid (404)."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(
        post_status_code=404, post_body={"message": "Unknown Guild"}
    )

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


def test_archive_channel_renames_to_done_prefix() -> None:
    """archive_channel PATCHes channel name to 'done-{slug}'."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(patch_status_code=200)

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        automator.archive_channel("ch-001", "Website Redesign")

    client = client_manager.__enter__.return_value
    client.patch.assert_called_once_with(
        "https://discord.com/api/v10/channels/ch-001",
        headers={
            "Authorization": "Bot token",
            "Content-Type": "application/json",
        },
        json={"name": "done-website-redesign"},
    )


def test_archive_channel_raises_on_api_error() -> None:
    """DiscordChannelError raised when rename returns non-200."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(patch_status_code=500)

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        with pytest.raises(DiscordChannelError):
            automator.archive_channel("ch-err", "Website Redesign")


def test_lock_channel_renames_to_closed_and_sets_readonly() -> None:
    """lock_channel PATCHes name to 'closed-{slug}' and PUTs deny permissions."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(patch_status_code=200, put_status_code=204)

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        automator.lock_channel("ch-002", "Website Redesign", "guild-002")

    client = client_manager.__enter__.return_value
    client.patch.assert_called_once_with(
        "https://discord.com/api/v10/channels/ch-002",
        headers={
            "Authorization": "Bot token",
            "Content-Type": "application/json",
        },
        json={"name": "closed-website-redesign"},
    )
    client.put.assert_called_once_with(
        "https://discord.com/api/v10/channels/ch-002/permissions/guild-002",
        headers={
            "Authorization": "Bot token",
            "Content-Type": "application/json",
        },
        json={"type": 0, "allow": "0", "deny": "2048"},
    )


def test_lock_channel_raises_if_rename_fails() -> None:
    """DiscordChannelError raised when rename step returns non-200."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(patch_status_code=500)

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        with pytest.raises(DiscordChannelError):
            automator.lock_channel("ch-003", "Website Redesign", "guild-003")

    client = client_manager.__enter__.return_value
    client.put.assert_not_called()


def test_lock_channel_raises_if_permissions_fail() -> None:
    """DiscordChannelError raised when permission PUT returns non-200."""

    automator = DiscordChannelAutomator(bot_token="token")
    client_manager = _mock_httpx_client(patch_status_code=200, put_status_code=500)

    with patch(
        "openqilin.project_spaces.discord_automator.httpx.Client",
        return_value=client_manager,
    ):
        with pytest.raises(DiscordChannelError):
            automator.lock_channel("ch-004", "Website Redesign", "guild-004")
