"""Async entrypoint for the OpenQilin real Discord bot worker."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import discord
import httpx
import structlog

from openqilin.discord_runtime.bridge import (
    DiscordCommandParseError,
    ParsedDiscordCommand,
    build_discord_ingress_payload,
    format_governed_response,
    parse_actor_role_map,
    parse_discord_command,
)
from openqilin.discord_runtime.role_bot_registry import (
    RoleBotRegistryError,
    build_role_bot_registry,
)
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.settings import get_settings
from openqilin.shared_kernel.startup_validation import (
    enforce_connector_secret_hardening,
    enforce_discord_role_bot_registry,
)

LOGGER = structlog.get_logger(__name__)
READY_MARKER_PATH = Path("/tmp/openqilin.discord_bot_worker.ready")


def _mark_ready() -> None:
    """Emit deterministic ready marker for container health checks."""

    READY_MARKER_PATH.write_text("ready\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class DiscordBotWorkerConfig:
    """Runtime configuration for Discord bot ingress bridge."""

    bot_role: str
    bot_id: str
    token: str
    control_plane_base_url: str
    connector_shared_secret: str
    command_prefix: str
    actor_role_default: str
    actor_role_map: dict[str, str]
    allowed_guild_ids: frozenset[str]
    allowed_channel_ids: frozenset[str]
    request_timeout_seconds: float
    response_chunk_size_chars: int
    response_retry_attempts: int
    response_retry_base_delay_seconds: float
    grafana_public_url: str = ""


@dataclass(frozen=True, slots=True)
class DiscordWorkerLaunchPlan:
    """Launch plan for one or many Discord bot clients."""

    configs: tuple[DiscordBotWorkerConfig, ...]
    required_roles: frozenset[str]


@dataclass(frozen=True, slots=True)
class DiscordInboundEvent:
    """Normalized Discord event emitted by one role-bot client."""

    bot_role: str
    bot_id: str
    bot_user_id: str
    parsed_command: ParsedDiscordCommand
    message_id: str
    actor_external_id: str
    actor_role: str
    content: str
    guild_id: str
    channel_id: str
    channel_type: str
    chat_class: str
    project_id: str | None
    timestamp: datetime
    response_channel: Any


@dataclass(slots=True)
class _RoleResponseOrderingState:
    """Best-effort ordered delivery state for one source message in one channel."""

    ordered_roles: tuple[str, ...]
    completed_roles: set[str]
    next_index: int
    condition: asyncio.Condition


class DiscordRoleBotReadiness:
    """Aggregated readiness state across required role bots."""

    def __init__(
        self,
        *,
        required_roles: frozenset[str],
        bot_id_by_role: dict[str, str],
        marker_path: Path = READY_MARKER_PATH,
    ) -> None:
        self._required_roles = required_roles
        self._bot_id_by_role = bot_id_by_role
        self._marker_path = marker_path
        self._ready_user_ids_by_role: dict[str, str] = {}
        self._lock = asyncio.Lock()

    @property
    def ready_roles(self) -> frozenset[str]:
        return frozenset(self._ready_user_ids_by_role.keys())

    @property
    def is_healthy(self) -> bool:
        return self._required_roles.issubset(self.ready_roles)

    async def mark_ready(self, *, role: str, user_id: str) -> None:
        async with self._lock:
            self._ready_user_ids_by_role[role] = user_id
            self._sync_ready_marker()

    async def mark_offline(self, *, role: str) -> None:
        async with self._lock:
            self._ready_user_ids_by_role.pop(role, None)
            self._sync_ready_marker()

    async def resolve_mentioned_recipients(
        self, *, mentioned_bot_user_ids: frozenset[str]
    ) -> tuple[tuple[tuple[str, str], ...], frozenset[str]]:
        async with self._lock:
            role_by_user_id = {
                user_id: role for role, user_id in self._ready_user_ids_by_role.items()
            }
            unresolved_user_ids = frozenset(
                user_id for user_id in mentioned_bot_user_ids if user_id not in role_by_user_id
            )
            recipients = tuple(
                sorted(
                    (
                        (self._bot_id_by_role[role], role)
                        for role, user_id in self._ready_user_ids_by_role.items()
                        if user_id in mentioned_bot_user_ids
                    ),
                    key=lambda item: (item[1], item[0]),
                )
            )
            return recipients, unresolved_user_ids

    def _sync_ready_marker(self) -> None:
        if self.is_healthy:
            self._marker_path.write_text("ready\n", encoding="utf-8")
            return
        if self._marker_path.exists():
            self._marker_path.unlink()


class DiscordIngressFanIn:
    """Shared ingress dispatcher used by one or many Discord bot clients."""

    def __init__(
        self,
        *,
        control_plane_base_url: str,
        connector_shared_secret: str,
        request_timeout_seconds: float,
        response_chunk_size_chars: int,
        response_retry_attempts: int,
        response_retry_base_delay_seconds: float,
    ) -> None:
        self._http_client = httpx.AsyncClient(timeout=request_timeout_seconds)
        self._ingress_url = f"{control_plane_base_url.rstrip('/')}/v1/connectors/discord/messages"
        self._connector_shared_secret = connector_shared_secret
        self._response_chunk_size_chars = max(200, response_chunk_size_chars)
        self._response_retry_attempts = max(0, response_retry_attempts)
        self._response_retry_base_delay_seconds = max(0.1, response_retry_base_delay_seconds)
        self._ordering_lock = asyncio.Lock()
        self._ordering_by_message_key: dict[tuple[str, str, str], _RoleResponseOrderingState] = {}

    async def close(self) -> None:
        await self._http_client.aclose()

    async def process_event(self, event: DiscordInboundEvent) -> None:
        payload, signature = build_discord_ingress_payload(
            parsed_command=event.parsed_command,
            message_id=event.message_id,
            actor_external_id=event.actor_external_id,
            actor_role=event.actor_role,
            content=event.content,
            guild_id=event.guild_id,
            channel_id=event.channel_id,
            channel_type=event.channel_type,
            chat_class=event.chat_class,
            connector_shared_secret=self._connector_shared_secret,
            project_id=event.project_id,
            timestamp=event.timestamp,
            bot_role=event.bot_role,
            bot_id=event.bot_id,
            bot_user_id=event.bot_user_id,
        )
        try:
            response = await self._http_client.post(
                self._ingress_url,
                headers={"X-OpenQilin-Signature": signature},
                json=payload,
            )
        except httpx.HTTPError as error:
            LOGGER.warning(
                "discord.worker.connector_error",
                message_id=event.message_id,
                bot_role=event.bot_role,
                error=str(error),
            )
            await event.response_channel.send(
                "[error] code=connector_http_error message=failed to reach OpenQilin control plane"
            )
            return
        try:
            body = response.json()
        except ValueError:
            body = {
                "status": "error",
                "trace_id": payload["trace_id"],
                "error": {
                    "code": "connector_response_invalid_json",
                    "message": "control plane returned invalid JSON",
                },
            }
        response_text = format_governed_response(status_code=response.status_code, body=body)
        await self._deliver_response(event=event, response_text=response_text)

    async def _deliver_response(self, *, event: DiscordInboundEvent, response_text: str) -> None:
        ordering_key, ordering_state = await self._enter_response_order(event=event)
        try:
            chunks = _chunk_discord_message(
                response_text,
                max_chunk_chars=self._response_chunk_size_chars,
            )
            total_chunks = len(chunks)
            for index, chunk in enumerate(chunks, start=1):
                outbound = chunk
                if total_chunks > 1:
                    outbound = f"[{event.bot_role} {index}/{total_chunks}] {chunk}"
                await self._send_with_retry(channel=event.response_channel, message=outbound)
        finally:
            await self._exit_response_order(
                ordering_key=ordering_key,
                ordering_state=ordering_state,
                role=event.bot_role,
            )

    async def _send_with_retry(self, *, channel: Any, message: str) -> None:
        attempts = self._response_retry_attempts + 1
        for attempt in range(attempts):
            try:
                await channel.send(message)
                return
            except Exception as error:
                is_transient = _is_transient_delivery_error(error)
                if attempt >= attempts - 1 or not is_transient:
                    raise
                delay_seconds = self._response_retry_base_delay_seconds * (2**attempt)
                LOGGER.warning(
                    "discord.worker.response_retry",
                    attempt=attempt + 1,
                    delay_seconds=delay_seconds,
                    error=str(error),
                )
                await asyncio.sleep(delay_seconds)

    async def _enter_response_order(
        self, *, event: DiscordInboundEvent
    ) -> tuple[tuple[str, str, str], _RoleResponseOrderingState]:
        ordering_key = (event.guild_id, event.channel_id, event.message_id)
        ordered_roles = _ordered_recipient_roles(
            recipients=event.parsed_command.recipients,
            fallback_role=event.bot_role,
        )
        async with self._ordering_lock:
            ordering_state = self._ordering_by_message_key.get(ordering_key)
            if ordering_state is None:
                ordering_state = _RoleResponseOrderingState(
                    ordered_roles=ordered_roles,
                    completed_roles=set(),
                    next_index=0,
                    condition=asyncio.Condition(),
                )
                self._ordering_by_message_key[ordering_key] = ordering_state
        async with ordering_state.condition:
            while (
                ordering_state.next_index < len(ordering_state.ordered_roles)
                and ordering_state.ordered_roles[ordering_state.next_index] != event.bot_role
            ):
                try:
                    await asyncio.wait_for(ordering_state.condition.wait(), timeout=6.0)
                except TimeoutError:
                    LOGGER.warning(
                        "discord.worker.response_order_timeout",
                        guild_id=event.guild_id,
                        channel_id=event.channel_id,
                        message_id=event.message_id,
                        bot_role=event.bot_role,
                    )
                    break
        return ordering_key, ordering_state

    async def _exit_response_order(
        self,
        *,
        ordering_key: tuple[str, str, str],
        ordering_state: _RoleResponseOrderingState,
        role: str,
    ) -> None:
        finished = False
        async with ordering_state.condition:
            ordering_state.completed_roles.add(role)
            while (
                ordering_state.next_index < len(ordering_state.ordered_roles)
                and ordering_state.ordered_roles[ordering_state.next_index]
                in ordering_state.completed_roles
            ):
                ordering_state.next_index += 1
            finished = len(ordering_state.completed_roles) >= len(ordering_state.ordered_roles)
            ordering_state.condition.notify_all()
        if finished:
            async with self._ordering_lock:
                existing = self._ordering_by_message_key.get(ordering_key)
                if existing is ordering_state:
                    self._ordering_by_message_key.pop(ordering_key, None)


def _channel_type_name(channel: Any) -> str:
    if isinstance(channel, discord.DMChannel):
        return "dm"
    if isinstance(channel, discord.GroupChannel):
        return "group"
    if isinstance(channel, discord.Thread):
        return "thread"
    return "text"


def _resolve_chat_class(channel: Any) -> str:
    if isinstance(channel, (discord.DMChannel, discord.GroupChannel)):
        return "direct"
    channel_name = getattr(channel, "name", "")
    normalized = str(channel_name).strip().lower().replace("-", "_")
    if normalized == "leadership_council" or normalized.startswith("leadership_council_"):
        return "leadership_council"
    if normalized == "governance" or normalized.startswith("governance_"):
        return "governance"
    if normalized == "executive" or normalized.startswith("executive_"):
        return "executive"
    return "project"


def _derive_project_id(channel: Any) -> str | None:
    channel_name = str(getattr(channel, "name", "")).strip().lower()
    if not channel_name:
        return None
    base = channel_name
    if base.startswith("project-"):
        base = base[len("project-") :]
    elif base.startswith("project_"):
        base = base[len("project_") :]
    normalized = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_" for character in base
    ).replace("-", "_")
    normalized = normalized.strip("_")
    return normalized or None


def _parse_id_allowlist(raw_value: str) -> frozenset[str]:
    normalized = tuple(
        item.strip() for item in raw_value.split(",") if item is not None and item.strip()
    )
    return frozenset(normalized)


def _resolve_worker_role(raw_value: str) -> str:
    normalized = raw_value.strip().lower()
    if not normalized:
        raise RuntimeError("discord worker role is required for discord_bot_worker")
    return normalized


def _resolve_worker_identity(settings: RuntimeSettings) -> tuple[str, str, str, frozenset[str]]:
    worker_role = _resolve_worker_role(settings.discord_worker_role)
    try:
        registry = build_role_bot_registry(settings)
    except RoleBotRegistryError as error:
        raise RuntimeError(
            f"invalid Discord role-bot registry: {error.code} {error.message}"
        ) from error
    identity = registry.identities_by_role.get(worker_role)
    if identity is None:
        raise RuntimeError(f"discord role-bot identity missing for worker role '{worker_role}'")
    if identity.status != "active":
        raise RuntimeError(
            f"discord role-bot identity for worker role '{worker_role}' is not active"
        )
    token = identity.token.strip()
    if not token:
        raise RuntimeError(
            f"discord role-bot identity for worker role '{worker_role}' has no token"
        )
    return (worker_role, identity.bot_id, token, frozenset(identity.guild_allowlist))


def _merge_guild_allowlists(
    *, worker_allowlist: frozenset[str], env_allowlist: frozenset[str]
) -> frozenset[str]:
    if len(worker_allowlist) == 0:
        return env_allowlist
    if len(env_allowlist) == 0:
        return worker_allowlist
    merged = worker_allowlist.intersection(env_allowlist)
    if len(merged) == 0:
        raise RuntimeError(
            "discord allowed guild allowlist intersection is empty for configured worker role"
        )
    return merged


class DiscordRecipientResolutionError(ValueError):
    """Raised when DM/mention recipient resolution fails closed."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _recipients_equal(
    left: tuple[tuple[str, str], ...], right: tuple[tuple[str, str], ...]
) -> bool:
    return len(left) == len(right) and set(left) == set(right)


def _is_runtime_placeholder_recipients(recipients: tuple[tuple[str, str], ...]) -> bool:
    return recipients == (("runtime", "runtime"),)


def _strip_leading_mentions(content: str) -> str:
    """Strip leading Discord @mention tokens (e.g. <@123> or <@!123>) from content."""

    return re.sub(r"^(<@!?\d+>\s*)+", "", content).strip()


def _coerce_free_text_to_ask_command(
    *,
    parsed: ParsedDiscordCommand | None,
    message_content: str,
) -> ParsedDiscordCommand | None:
    """Normalize free-text messages into runtime ask commands."""

    if parsed is not None:
        return parsed
    stripped_content = message_content.strip()
    if not stripped_content:
        return None
    return ParsedDiscordCommand(
        action="ask",
        target=None,
        args=(stripped_content,),
        recipients=(("runtime", "runtime"),),
        project_id=None,
        priority="normal",
    )


def _chunk_discord_message(text: str, *, max_chunk_chars: int) -> tuple[str, ...]:
    normalized = text.strip()
    if not normalized:
        return ("[no content]",)
    if len(normalized) <= max_chunk_chars:
        return (normalized,)

    chunks: list[str] = []
    remaining = normalized
    while remaining:
        if len(remaining) <= max_chunk_chars:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_chunk_chars + 1)
        if cut < max_chunk_chars // 2:
            cut = remaining.rfind(" ", 0, max_chunk_chars + 1)
        if cut <= 0:
            cut = max_chunk_chars
        chunk = remaining[:cut].rstrip()
        if not chunk:
            chunk = remaining[:max_chunk_chars]
            cut = max_chunk_chars
        chunks.append(chunk)
        remaining = remaining[cut:].lstrip()
    return tuple(chunks)


def _is_transient_delivery_error(error: Exception) -> bool:
    status = getattr(error, "status", None)
    if isinstance(status, int) and status in {429, 500, 502, 503, 504}:
        return True
    return False


def _role_priority(role: str) -> int:
    order = {
        "administrator": 0,
        "auditor": 1,
        "ceo": 2,
        "cwo": 3,
        "project_manager": 4,
        "runtime_agent": 5,
    }
    return order.get(role.strip().lower(), 50)


def _ordered_recipient_roles(
    *, recipients: tuple[tuple[str, str], ...], fallback_role: str
) -> tuple[str, ...]:
    roles = {
        recipient_type.strip().lower() for _, recipient_type in recipients if recipient_type.strip()
    }
    if fallback_role.strip():
        roles.add(fallback_role.strip().lower())
    if not roles:
        return (fallback_role.strip().lower() or "runtime_agent",)
    return tuple(sorted(roles, key=lambda item: (_role_priority(item), item)))


def resolve_discord_recipients(
    *,
    parsed_recipients: tuple[tuple[str, str], ...],
    chat_class: str,
    target_bot_role: str,
    target_bot_id: str,
    mentioned_bot_user_ids: frozenset[str],
    mention_recipients: tuple[tuple[str, str], ...],
    unresolved_mentions: frozenset[str],
) -> tuple[tuple[str, str], ...]:
    """Resolve governed recipients for DM and mention-based group routing."""

    expected_dm_recipients = ((target_bot_id, target_bot_role),)
    if chat_class == "direct":
        if not _is_runtime_placeholder_recipients(parsed_recipients) and not _recipients_equal(
            parsed_recipients, expected_dm_recipients
        ):
            raise DiscordRecipientResolutionError(
                code="recipient_mismatch",
                message=(
                    "direct message recipient mismatch; recipient must match target role bot "
                    f"{target_bot_role}"
                ),
            )
        return expected_dm_recipients

    if len(mentioned_bot_user_ids) == 0:
        if _is_runtime_placeholder_recipients(parsed_recipients):
            # No explicit mention but runtime-placeholder recipients — let the
            # control plane FreeTextRouter determine the actual recipient.
            return (("runtime", "runtime"),)
        raise DiscordRecipientResolutionError(
            code="recipient_mentions_required",
            message="group chat command requires explicit role-bot mention(s)",
        )
    if len(unresolved_mentions) > 0:
        raise DiscordRecipientResolutionError(
            code="recipient_mention_unresolved",
            message=(
                "one or more mentioned role bots are not online/registered: "
                + ", ".join(sorted(unresolved_mentions))
            ),
        )
    if len(mention_recipients) == 0:
        raise DiscordRecipientResolutionError(
            code="recipient_mentions_required",
            message="group chat command did not resolve any governed role recipient",
        )
    if not _is_runtime_placeholder_recipients(parsed_recipients) and not _recipients_equal(
        parsed_recipients, mention_recipients
    ):
        raise DiscordRecipientResolutionError(
            code="recipient_mismatch",
            message="recipient list does not match explicitly mentioned role bots",
        )
    return mention_recipients


def _build_worker_config_from_identity(
    settings: RuntimeSettings,
    *,
    worker_role: str,
    worker_bot_id: str,
    token: str,
    worker_allowlist: frozenset[str],
) -> DiscordBotWorkerConfig:
    env_allowlist = _parse_id_allowlist(settings.discord_allowed_guild_ids_csv)
    return DiscordBotWorkerConfig(
        bot_role=worker_role,
        bot_id=worker_bot_id,
        token=token.strip(),
        control_plane_base_url=settings.discord_control_plane_base_url,
        connector_shared_secret=settings.connector_shared_secret,
        command_prefix=settings.discord_command_prefix,
        actor_role_default=settings.discord_actor_role_default,
        actor_role_map=parse_actor_role_map(settings.discord_actor_role_map_json),
        allowed_guild_ids=_merge_guild_allowlists(
            worker_allowlist=worker_allowlist,
            env_allowlist=env_allowlist,
        ),
        allowed_channel_ids=_parse_id_allowlist(settings.discord_allowed_channel_ids_csv),
        request_timeout_seconds=settings.discord_request_timeout_seconds,
        response_chunk_size_chars=max(200, settings.discord_response_chunk_size_chars),
        response_retry_attempts=max(0, settings.discord_response_retry_attempts),
        response_retry_base_delay_seconds=max(
            0.1, settings.discord_response_retry_base_delay_seconds
        ),
        grafana_public_url=settings.grafana_public_url,
    )


def build_multi_worker_configs(settings: RuntimeSettings) -> tuple[DiscordBotWorkerConfig, ...]:
    """Resolve all active role-bot configs when multi-bot mode is enabled."""

    try:
        registry = build_role_bot_registry(settings)
    except RoleBotRegistryError as error:
        raise RuntimeError(
            f"invalid Discord role-bot registry: {error.code} {error.message}"
        ) from error

    configs: list[DiscordBotWorkerConfig] = []
    for role, identity in registry.identities_by_role.items():
        if identity.status != "active":
            continue
        token = identity.token.strip()
        if not token:
            raise RuntimeError(f"discord role-bot identity for worker role '{role}' has no token")
        configs.append(
            _build_worker_config_from_identity(
                settings,
                worker_role=role,
                worker_bot_id=identity.bot_id,
                token=token,
                worker_allowlist=frozenset(identity.guild_allowlist),
            )
        )
    if len(configs) == 0:
        raise RuntimeError("discord multi-bot mode requires at least one active role-bot config")
    return tuple(configs)


def build_worker_launch_plan(settings: RuntimeSettings) -> DiscordWorkerLaunchPlan:
    """Build launch plan for single-bot or multi-bot runtime mode."""

    if settings.discord_multi_bot_enabled:
        configs = build_multi_worker_configs(settings)
        required_roles = frozenset(
            item.strip().lower()
            for item in settings.discord_required_role_bots_csv.split(",")
            if item.strip()
        )
        if len(required_roles) == 0:
            required_roles = frozenset(config.bot_role for config in configs)
        return DiscordWorkerLaunchPlan(configs=configs, required_roles=required_roles)

    config = build_worker_config(settings)
    return DiscordWorkerLaunchPlan(
        configs=(config,),
        required_roles=frozenset({config.bot_role}),
    )


def _infer_recipients_from_mentions(
    message: discord.Message,
) -> tuple[tuple[str, str], ...]:
    """Infer recipient tuples from bot display names when role resolution fails.

    Used when a bot is mentioned but its Discord user ID is not in this process's
    readiness registry (multi-process deployment scenario). Extracts the role name
    from the bot's display name using the "OpenQilin <Role>" naming convention.
    Returns ``(("runtime", "runtime"),)`` if no role can be inferred.
    """
    roles: list[tuple[str, str]] = []
    for user in message.mentions:
        if not getattr(user, "bot", False):
            continue
        display = (user.display_name or user.name or "").strip().lower()
        for prefix in ("openqilin ", "openqilin_"):
            if display.startswith(prefix):
                role = display[len(prefix) :].replace(" ", "_").replace("-", "_")
                if role and role not in ("runtime",):
                    roles.append((str(user.id), role))
                break
    return tuple(roles) if roles else (("runtime", "runtime"),)


class OpenQilinDiscordClient(discord.Client):
    """Discord gateway client that bridges inbound messages to governed ingress."""

    def __init__(
        self,
        *,
        config: DiscordBotWorkerConfig,
        fan_in: DiscordIngressFanIn,
        readiness: DiscordRoleBotReadiness,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._config = config
        self._fan_in = fan_in
        self._readiness = readiness

    async def close(self) -> None:
        await super().close()

    async def on_ready(self) -> None:
        bot_user_id = str(self.user.id) if self.user is not None else "unknown"
        await self._readiness.mark_ready(role=self._config.bot_role, user_id=bot_user_id)
        LOGGER.info(
            "discord.worker.ready",
            bot_user=str(self.user),
            bot_role=self._config.bot_role,
            bot_id=self._config.bot_id,
            control_plane_base_url=self._config.control_plane_base_url,
        )
        # M15-WP6: Announce Grafana dashboard URL in #leadership_council on startup.
        # Only the runtime_agent bot announces — avoids duplicate messages in multi-bot mode.
        if self._config.bot_role == "runtime_agent" and self._config.grafana_public_url:
            from openqilin.apps.discord_automator import announce_grafana_dashboard_url

            await announce_grafana_dashboard_url(self, self._config.grafana_public_url)

    async def on_disconnect(self) -> None:
        await self._readiness.mark_offline(role=self._config.bot_role)
        LOGGER.warning(
            "discord.worker.disconnected",
            bot_role=self._config.bot_role,
            bot_id=self._config.bot_id,
        )

    async def _resolve_recipients(
        self, *, parsed: ParsedDiscordCommand, chat_class: str, message: discord.Message
    ) -> tuple[tuple[str, str], ...]:
        mentioned_bot_user_ids = frozenset(
            str(user.id) for user in message.mentions if getattr(user, "bot", False)
        )
        (
            mention_recipients,
            unresolved_mentions,
        ) = await self._readiness.resolve_mentioned_recipients(
            mentioned_bot_user_ids=mentioned_bot_user_ids
        )
        return resolve_discord_recipients(
            parsed_recipients=parsed.recipients,
            chat_class=chat_class,
            target_bot_role=self._config.bot_role,
            target_bot_id=self._config.bot_id,
            mentioned_bot_user_ids=mentioned_bot_user_ids,
            mention_recipients=mention_recipients,
            unresolved_mentions=unresolved_mentions,
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        guild_id = str(message.guild.id) if message.guild is not None else "dm"
        channel_id = str(message.channel.id)
        if (
            len(self._config.allowed_guild_ids) > 0
            and guild_id not in self._config.allowed_guild_ids
        ):
            LOGGER.info(
                "discord.worker.message_ignored",
                reason="guild_not_allowlisted",
                guild_id=guild_id,
                channel_id=channel_id,
                message_id=str(message.id),
            )
            return
        if (
            len(self._config.allowed_channel_ids) > 0
            and channel_id not in self._config.allowed_channel_ids
        ):
            LOGGER.info(
                "discord.worker.message_ignored",
                reason="channel_not_allowlisted",
                guild_id=guild_id,
                channel_id=channel_id,
                message_id=str(message.id),
            )
            return
        _content_for_parse = _strip_leading_mentions(message.content)
        _is_explicit_command = _content_for_parse.startswith(self._config.command_prefix)
        try:
            parsed = parse_discord_command(
                _content_for_parse,
                command_prefix=self._config.command_prefix,
            )
        except DiscordCommandParseError as error:
            await message.channel.send(
                f"[error] code=discord_command_parse_error message={error.message}"
            )
            return
        parsed = _coerce_free_text_to_ask_command(
            parsed=parsed,
            message_content=message.content,
        )
        if parsed is None:
            return
        actor_id = str(message.author.id)
        actor_role = self._config.actor_role_map.get(actor_id, self._config.actor_role_default)
        channel_type = _channel_type_name(message.channel)
        chat_class = _resolve_chat_class(message.channel)

        # DM gate for non-Secretary bots: free-text DMs are not routed through the Secretary
        # advisory bypass on behalf of another bot — that produces confusing "I am Secretary"
        # responses delivered via a different bot's channel.
        # For free-text DMs, post a usage hint and return. Explicit /oq commands in DMs are
        # still processed normally.
        if (
            chat_class == "direct"
            and not _is_explicit_command
            and self._config.bot_role != "secretary"
        ):
            await message.channel.send(
                f"To send me a query, use: `/oq ask {self._config.bot_role} <your question>`\n"
                f"Or DM @OpenQilin Secretary for general routing assistance."
            )
            return

        # Free-text group-channel gate: non-Secretary bots silently skip free-text messages.
        # Apply BEFORE recipient resolution to prevent spurious [denied] errors when a bot
        # mentioned in the message runs in a different process.
        if chat_class != "direct" and not _is_explicit_command:
            if self._config.bot_role != "secretary":
                return

        try:
            resolved_recipients = await self._resolve_recipients(
                parsed=parsed,
                chat_class=chat_class,
                message=message,
            )
        except DiscordRecipientResolutionError as error:
            if (
                not _is_explicit_command
                and self._config.bot_role == "secretary"
                and error.code == "recipient_mention_unresolved"
            ):
                # A bot was mentioned but its user ID is not in this process's registry
                # (multi-process deployment: each bot only knows its own user ID at runtime).
                # Infer the recipient role from the bot's display name so Secretary can
                # still provide routing guidance for the addressed agent.
                resolved_recipients = _infer_recipients_from_mentions(message)
            else:
                await message.channel.send(f"[denied] code={error.code} message={error.message}")
                return
        # Group-channel single-bot gate.
        # DMs are always 1:1 so no gate needed there.
        if chat_class != "direct":
            if not _is_explicit_command:
                # Free-text (no /oq prefix): Secretary is the sole group-channel handler.
                # This prevents @Auditor free-text being displayed via Auditor with Secretary text.
                if self._config.bot_role != "secretary":
                    return
            else:
                # Explicit /oq command: only the @mentioned bot (resolved recipient) handles it.
                _this_bot_is_target = any(
                    r[0] == self._config.bot_id or r[1] == self._config.bot_role
                    for r in resolved_recipients
                )
                if not _this_bot_is_target:
                    return
        project_id = parsed.project_id
        if project_id is None and chat_class == "project":
            project_id = _derive_project_id(message.channel)
        normalized_command = ParsedDiscordCommand(
            action=parsed.action,
            target=parsed.target,
            args=parsed.args,
            recipients=resolved_recipients,
            project_id=parsed.project_id,
            priority=parsed.priority,
        )
        bot_user_id = str(self.user.id) if self.user is not None else self._config.bot_id
        event = DiscordInboundEvent(
            bot_role=self._config.bot_role,
            bot_id=self._config.bot_id,
            bot_user_id=bot_user_id,
            parsed_command=normalized_command,
            message_id=str(message.id),
            actor_external_id=actor_id,
            actor_role=actor_role,
            content=message.content,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
            chat_class=chat_class,
            project_id=project_id,
            timestamp=message.created_at,
            response_channel=message.channel,
        )
        await self._fan_in.process_event(event)


def build_worker_config(settings: RuntimeSettings) -> DiscordBotWorkerConfig:
    """Resolve Discord worker runtime config from settings and env fallbacks."""

    worker_role, worker_bot_id, token, worker_allowlist = _resolve_worker_identity(settings)
    return _build_worker_config_from_identity(
        settings,
        worker_role=worker_role,
        worker_bot_id=worker_bot_id,
        token=token,
        worker_allowlist=worker_allowlist,
    )


async def run_worker_launch_plan(plan: DiscordWorkerLaunchPlan) -> None:
    """Run one or many Discord bot clients according to launch plan."""

    primary_config = plan.configs[0]
    readiness = DiscordRoleBotReadiness(
        required_roles=plan.required_roles,
        bot_id_by_role={config.bot_role: config.bot_id for config in plan.configs},
    )
    fan_in = DiscordIngressFanIn(
        control_plane_base_url=primary_config.control_plane_base_url,
        connector_shared_secret=primary_config.connector_shared_secret,
        request_timeout_seconds=primary_config.request_timeout_seconds,
        response_chunk_size_chars=primary_config.response_chunk_size_chars,
        response_retry_attempts=primary_config.response_retry_attempts,
        response_retry_base_delay_seconds=primary_config.response_retry_base_delay_seconds,
    )
    clients = [
        OpenQilinDiscordClient(
            config=config,
            fan_in=fan_in,
            readiness=readiness,
        )
        for config in plan.configs
    ]
    try:
        await asyncio.gather(
            *(client.start(config.token) for client, config in zip(clients, plan.configs)),
        )
    finally:
        await asyncio.gather(*(client.close() for client in clients), return_exceptions=True)
        await fan_in.close()


async def main(*, run_once: bool = False) -> None:
    """Run Discord bot worker bootstrap and gateway loop."""

    settings = get_settings()
    enforce_connector_secret_hardening(settings)
    enforce_discord_role_bot_registry(settings)
    LOGGER.info("worker.bootstrap", worker="discord_bot_worker")
    if run_once:
        _mark_ready()
        return
    launch_plan = build_worker_launch_plan(settings)
    LOGGER.info(
        "discord.worker.launch_plan",
        multi_bot=settings.discord_multi_bot_enabled,
        bot_count=len(launch_plan.configs),
        required_roles=sorted(launch_plan.required_roles),
        bot_roles=[config.bot_role for config in launch_plan.configs],
    )
    await run_worker_launch_plan(launch_plan)


if __name__ == "__main__":
    asyncio.run(main())
