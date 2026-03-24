"""Unit tests for Redis-backed bot registry reader."""

from __future__ import annotations

from unittest.mock import MagicMock

from openqilin.control_plane.advisory.bot_registry_reader import BotRegistryReader


def test_get_mention_present_str() -> None:
    redis_client = MagicMock(hget=MagicMock(return_value="1234567890"))

    mention = BotRegistryReader(redis_client=redis_client).get_mention("auditor")

    assert mention == "<@1234567890>"


def test_get_mention_present_bytes() -> None:
    redis_client = MagicMock(hget=MagicMock(return_value=b"9876543210"))

    mention = BotRegistryReader(redis_client=redis_client).get_mention("auditor")

    assert mention == "<@9876543210>"


def test_get_mention_absent() -> None:
    redis_client = MagicMock(hget=MagicMock(return_value=None))

    mention = BotRegistryReader(redis_client=redis_client).get_mention("auditor")

    assert mention is None


def test_get_mention_redis_error() -> None:
    redis_client = MagicMock(hget=MagicMock(side_effect=Exception("boom")))

    mention = BotRegistryReader(redis_client=redis_client).get_mention("auditor")

    assert mention is None


def test_get_all_returns_decoded_dict() -> None:
    redis_client = MagicMock(hgetall=MagicMock(return_value={b"auditor": b"123"}))

    items = BotRegistryReader(redis_client=redis_client).get_all()

    assert items == {"auditor": "123"}


def test_get_all_redis_error() -> None:
    redis_client = MagicMock(hgetall=MagicMock(side_effect=Exception("boom")))

    items = BotRegistryReader(redis_client=redis_client).get_all()

    assert items == {}
