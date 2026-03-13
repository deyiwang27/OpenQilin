from __future__ import annotations

import pytest

from openqilin.apps.discord_bot_worker import (
    DiscordRecipientResolutionError,
    resolve_discord_recipients,
)


def test_m10_wp3_dm_routing_maps_to_target_role_bot() -> None:
    recipients = resolve_discord_recipients(
        parsed_recipients=(("runtime", "runtime"),),
        chat_class="direct",
        target_bot_role="ceo",
        target_bot_id="ceo_core",
        mentioned_bot_user_ids=frozenset(),
        mention_recipients=(),
        unresolved_mentions=frozenset(),
    )

    assert recipients == (("ceo_core", "ceo"),)


def test_m10_wp3_dm_routing_rejects_recipient_mismatch() -> None:
    with pytest.raises(DiscordRecipientResolutionError) as error:
        resolve_discord_recipients(
            parsed_recipients=(("auditor_core", "auditor"),),
            chat_class="direct",
            target_bot_role="ceo",
            target_bot_id="ceo_core",
            mentioned_bot_user_ids=frozenset(),
            mention_recipients=(),
            unresolved_mentions=frozenset(),
        )

    assert error.value.code == "recipient_mismatch"


def test_m10_wp3_group_routing_uses_only_explicit_mentions() -> None:
    recipients = resolve_discord_recipients(
        parsed_recipients=(("runtime", "runtime"),),
        chat_class="leadership_council",
        target_bot_role="ceo",
        target_bot_id="ceo_core",
        mentioned_bot_user_ids=frozenset({"1001", "1002"}),
        mention_recipients=(("auditor_core", "auditor"), ("ceo_core", "ceo")),
        unresolved_mentions=frozenset(),
    )

    assert recipients == (("auditor_core", "auditor"), ("ceo_core", "ceo"))


def test_m10_wp3_group_routing_rejects_no_mention() -> None:
    with pytest.raises(DiscordRecipientResolutionError) as error:
        resolve_discord_recipients(
            parsed_recipients=(("runtime", "runtime"),),
            chat_class="leadership_council",
            target_bot_role="ceo",
            target_bot_id="ceo_core",
            mentioned_bot_user_ids=frozenset(),
            mention_recipients=(),
            unresolved_mentions=frozenset(),
        )

    assert error.value.code == "recipient_mentions_required"


def test_m10_wp3_group_routing_rejects_unresolved_mentioned_bot() -> None:
    with pytest.raises(DiscordRecipientResolutionError) as error:
        resolve_discord_recipients(
            parsed_recipients=(("runtime", "runtime"),),
            chat_class="leadership_council",
            target_bot_role="ceo",
            target_bot_id="ceo_core",
            mentioned_bot_user_ids=frozenset({"1001"}),
            mention_recipients=(),
            unresolved_mentions=frozenset({"1001"}),
        )

    assert error.value.code == "recipient_mention_unresolved"


def test_m10_wp3_group_routing_rejects_payload_recipient_mismatch() -> None:
    with pytest.raises(DiscordRecipientResolutionError) as error:
        resolve_discord_recipients(
            parsed_recipients=(("ceo_core", "ceo"),),
            chat_class="leadership_council",
            target_bot_role="ceo",
            target_bot_id="ceo_core",
            mentioned_bot_user_ids=frozenset({"1001", "1002"}),
            mention_recipients=(("auditor_core", "auditor"), ("ceo_core", "ceo")),
            unresolved_mentions=frozenset(),
        )

    assert error.value.code == "recipient_mismatch"
