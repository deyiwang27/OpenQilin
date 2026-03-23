from __future__ import annotations

import pytest

from openqilin.apps.discord_bot_worker import (
    DiscordRecipientResolutionError,
    _coerce_free_text_to_ask_command,
    _strip_leading_mentions,
    resolve_discord_recipients,
)


def test_strip_leading_mentions_strips_multiple_prefix_mentions() -> None:
    stripped = _strip_leading_mentions('<@123>   <@!456> /oq ask "hello"')

    assert stripped == '/oq ask "hello"'


def test_strip_leading_mentions_leaves_non_prefix_mentions() -> None:
    stripped = _strip_leading_mentions("hello <@123>")

    assert stripped == "hello <@123>"


def test_free_text_message_creates_ask_command() -> None:
    """on_message forwards free-text (non-/oq) as action='ask' to control plane."""

    parsed = _coerce_free_text_to_ask_command(
        parsed=None,
        message_content="status update for the team",
    )

    assert parsed is not None
    assert parsed.action == "ask"
    assert parsed.args == ("status update for the team",)
    assert parsed.recipients == (("runtime", "runtime"),)


def test_empty_content_is_dropped() -> None:
    """on_message silently drops messages with empty content after stripping."""

    parsed = _coerce_free_text_to_ask_command(
        parsed=None,
        message_content="  \n\t  ",
    )

    assert parsed is None


def test_runtime_placeholder_bypasses_mention_requirement() -> None:
    """resolve_discord_recipients returns runtime tuple when no mention and runtime placeholder."""

    resolved = resolve_discord_recipients(
        parsed_recipients=(("runtime", "runtime"),),
        chat_class="leadership_council",
        target_bot_role="runtime_agent",
        target_bot_id="runtime",
        mentioned_bot_user_ids=frozenset(),
        mention_recipients=tuple(),
        unresolved_mentions=frozenset(),
    )

    assert resolved == (("runtime", "runtime"),)


def test_explicit_recipients_still_require_mention() -> None:
    """resolve_discord_recipients still raises when non-placeholder recipients and no mention."""

    with pytest.raises(DiscordRecipientResolutionError) as error:
        resolve_discord_recipients(
            parsed_recipients=(("secretary_bot", "secretary"),),
            chat_class="leadership_council",
            target_bot_role="runtime_agent",
            target_bot_id="runtime",
            mentioned_bot_user_ids=frozenset(),
            mention_recipients=tuple(),
            unresolved_mentions=frozenset(),
        )

    assert error.value.code == "recipient_mentions_required"
