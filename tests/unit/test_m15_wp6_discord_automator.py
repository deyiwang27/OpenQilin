from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from openqilin.apps.discord_automator import announce_grafana_dashboard_url


@pytest.mark.asyncio
async def test_empty_url_returns_immediately() -> None:
    mock_client = MagicMock()
    with patch.object(
        type(mock_client), "guilds", new_callable=PropertyMock, create=True
    ) as guilds_property:
        guilds_property.side_effect = AssertionError("guilds should not be accessed")
        await announce_grafana_dashboard_url(mock_client, "")
        guilds_property.assert_not_called()


@pytest.mark.asyncio
async def test_leadership_council_found_sends_message() -> None:
    channel = MagicMock()
    channel.name = "leadership_council"
    channel.send = AsyncMock()
    guild = MagicMock()
    guild.text_channels = [channel]
    client = MagicMock()
    client.guilds = [guild]

    dashboard_url = "http://grafana:3000/d/openqilin-main"
    await announce_grafana_dashboard_url(client, dashboard_url)

    channel.send.assert_awaited_once()
    assert dashboard_url in channel.send.await_args.args[0]


@pytest.mark.asyncio
async def test_channel_name_with_hyphen_matches() -> None:
    channel = MagicMock()
    channel.name = "leadership-council"
    channel.send = AsyncMock()
    guild = MagicMock()
    guild.text_channels = [channel]
    client = MagicMock()
    client.guilds = [guild]

    await announce_grafana_dashboard_url(client, "http://grafana:3000")

    channel.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_leadership_council_logs_warning() -> None:
    channel = MagicMock()
    channel.name = "general"
    channel.send = AsyncMock()
    guild = MagicMock()
    guild.text_channels = [channel]
    client = MagicMock()
    client.guilds = [guild]

    await announce_grafana_dashboard_url(client, "http://grafana:3000")

    channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_guilds_logs_warning() -> None:
    client = MagicMock()
    client.guilds = []

    await announce_grafana_dashboard_url(client, "http://grafana:3000")


@pytest.mark.asyncio
async def test_send_raises_logs_warning_no_exception() -> None:
    channel = MagicMock()
    channel.name = "leadership_council"
    channel.send = AsyncMock(side_effect=Exception("discord error"))
    guild = MagicMock()
    guild.text_channels = [channel]
    client = MagicMock()
    client.guilds = [guild]

    await announce_grafana_dashboard_url(client, "http://grafana:3000")

    channel.send.assert_awaited_once()
