"""Role-bot identity registry for Discord multi-bot configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from openqilin.shared_kernel.config import RuntimeSettings

_DEFAULT_REQUIRED_ROLE_BOTS = (
    "administrator",
    "auditor",
    "ceo",
    "cwo",
    "project_manager",
)


class RoleBotRegistryError(ValueError):
    """Raised when Discord role-bot registry configuration is invalid."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class RoleBotIdentity:
    """One configured Discord role-bot identity."""

    role: str
    bot_id: str
    token: str
    guild_allowlist: tuple[str, ...]
    status: str


@dataclass(frozen=True, slots=True)
class RoleBotRegistry:
    """Validated role-bot registry resolved from runtime settings."""

    identities_by_role: Mapping[str, RoleBotIdentity]
    required_roles: tuple[str, ...]


def build_role_bot_registry(settings: RuntimeSettings) -> RoleBotRegistry:
    """Resolve role-bot registry from runtime settings with fail-closed validation."""

    configured = _parse_role_identity_map(settings.discord_role_bot_tokens_json)

    if not configured and not settings.discord_multi_bot_enabled:
        fallback_token = (settings.discord_bot_token or "").strip()
        if fallback_token:
            configured = {
                "runtime_agent": RoleBotIdentity(
                    role="runtime_agent",
                    bot_id="runtime_agent",
                    token=fallback_token,
                    guild_allowlist=(),
                    status="active",
                )
            }

    if not configured:
        raise RoleBotRegistryError(
            code="discord_role_bot_registry_empty",
            message="discord role-bot token map is empty",
        )

    _assert_unique_tokens(configured)
    _assert_unique_bot_ids(configured)

    required_roles = _parse_required_roles(settings.discord_required_role_bots_csv)
    if settings.discord_multi_bot_enabled:
        missing = tuple(
            role
            for role in required_roles
            if role not in configured or configured[role].status != "active"
        )
        if missing:
            raise RoleBotRegistryError(
                code="discord_role_bot_required_missing",
                message="missing required role-bot tokens: " + ", ".join(missing),
            )
    return RoleBotRegistry(
        identities_by_role={role: configured[role] for role in sorted(configured.keys())},
        required_roles=required_roles,
    )


def _parse_role_identity_map(raw_value: str) -> dict[str, RoleBotIdentity]:
    normalized = raw_value.strip()
    if not normalized:
        return {}

    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError as error:
        raise RoleBotRegistryError(
            code="discord_role_bot_json_invalid",
            message="OPENQILIN_DISCORD_ROLE_BOT_TOKENS_JSON must be valid JSON object",
        ) from error

    if not isinstance(decoded, dict):
        raise RoleBotRegistryError(
            code="discord_role_bot_json_invalid",
            message="OPENQILIN_DISCORD_ROLE_BOT_TOKENS_JSON must be a JSON object",
        )

    result: dict[str, RoleBotIdentity] = {}
    for raw_role, raw_identity in decoded.items():
        role = str(raw_role).strip().lower()
        if not role:
            raise RoleBotRegistryError(
                code="discord_role_bot_role_invalid",
                message="role-bot role keys must be non-empty",
            )
        result[role] = _parse_role_identity(role=role, raw_identity=raw_identity)
    return result


def _parse_role_identity(*, role: str, raw_identity: Any) -> RoleBotIdentity:
    if isinstance(raw_identity, str):
        token = raw_identity.strip()
        if not token:
            raise RoleBotRegistryError(
                code="discord_role_bot_token_missing",
                message=f"role-bot token missing for role: {role}",
            )
        return RoleBotIdentity(
            role=role,
            bot_id=role,
            token=token,
            guild_allowlist=(),
            status="active",
        )

    if not isinstance(raw_identity, dict):
        raise RoleBotRegistryError(
            code="discord_role_bot_json_invalid",
            message=f"role-bot entry for role {role} must be string or object",
        )

    status = str(raw_identity.get("status", "active")).strip().lower() or "active"
    if status not in {"active", "disabled"}:
        raise RoleBotRegistryError(
            code="discord_role_bot_status_invalid",
            message=f"role-bot status must be active|disabled for role: {role}",
        )

    token = str(raw_identity.get("token", "")).strip()
    if status == "active" and not token:
        raise RoleBotRegistryError(
            code="discord_role_bot_token_missing",
            message=f"role-bot token missing for role: {role}",
        )

    bot_id = str(raw_identity.get("bot_id", role)).strip().lower()
    if not bot_id:
        raise RoleBotRegistryError(
            code="discord_role_bot_id_invalid",
            message=f"role-bot bot_id must be non-empty for role: {role}",
        )

    guild_allowlist = _parse_guild_allowlist(raw_identity.get("guild_allowlist"))
    return RoleBotIdentity(
        role=role,
        bot_id=bot_id,
        token=token,
        guild_allowlist=guild_allowlist,
        status=status,
    )


def _parse_guild_allowlist(raw_value: Any) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if isinstance(raw_value, str):
        candidates = [item.strip() for item in raw_value.split(",")]
    elif isinstance(raw_value, list):
        candidates = [str(item).strip() for item in raw_value]
    else:
        raise RoleBotRegistryError(
            code="discord_role_bot_guild_allowlist_invalid",
            message="role-bot guild_allowlist must be list or comma-separated string",
        )
    normalized = tuple(item for item in candidates if item)
    return normalized


def _assert_unique_tokens(role_to_identity: Mapping[str, RoleBotIdentity]) -> None:
    owners_by_token: dict[str, str] = {}
    for role, identity in role_to_identity.items():
        token = identity.token.strip()
        if not token:
            continue
        existing_role = owners_by_token.get(token)
        if existing_role is not None and existing_role != role:
            raise RoleBotRegistryError(
                code="discord_role_bot_token_duplicate",
                message=(
                    "discord role-bot tokens must be unique across roles; "
                    f"duplicate token for roles {existing_role} and {role}"
                ),
            )
        owners_by_token[token] = role


def _assert_unique_bot_ids(role_to_identity: Mapping[str, RoleBotIdentity]) -> None:
    owners_by_bot_id: dict[str, str] = {}
    for role, identity in role_to_identity.items():
        existing_role = owners_by_bot_id.get(identity.bot_id)
        if existing_role is not None and existing_role != role:
            raise RoleBotRegistryError(
                code="discord_role_bot_id_duplicate",
                message=(
                    "discord role-bot ids must be unique across roles; "
                    f"duplicate bot_id for roles {existing_role} and {role}"
                ),
            )
        owners_by_bot_id[identity.bot_id] = role


def _parse_required_roles(raw_value: str) -> tuple[str, ...]:
    values = tuple(item.strip().lower() for item in raw_value.split(",") if item.strip())
    if values:
        return values
    return _DEFAULT_REQUIRED_ROLE_BOTS
