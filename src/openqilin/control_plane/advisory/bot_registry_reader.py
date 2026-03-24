"""Redis-backed bot registry reader for Discord @mention handle lookup."""

from __future__ import annotations

from typing import Any

import structlog

LOGGER = structlog.get_logger(__name__)
BOT_REGISTRY_REDIS_KEY = "openqilin:bot_discord_ids"


def _decode_redis_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


class BotRegistryReader:
    """Read live bot Discord user IDs from the Redis bot registry hash."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def get_mention(self, role: str) -> str | None:
        """Return '<@user_id>' for the given role, or None if not registered.
        Never raises — returns None on Redis error.
        """

        try:
            user_id = self._redis.hget(BOT_REGISTRY_REDIS_KEY, role)
        except Exception:
            LOGGER.warning("bot_registry_reader.hget_failed", role=role)
            return None

        if user_id is None:
            return None

        return f"<@{_decode_redis_value(user_id)}>"

    def get_all(self) -> dict[str, str]:
        """Return full {role: user_id} dict. Returns {} on Redis error."""

        try:
            items = self._redis.hgetall(BOT_REGISTRY_REDIS_KEY)
        except Exception:
            LOGGER.warning("bot_registry_reader.hgetall_failed")
            return {}

        return {
            _decode_redis_value(role): _decode_redis_value(user_id)
            for role, user_id in items.items()
        }
