"""Utilities for Discord-to-governed-ingress request/response bridging."""

from __future__ import annotations

import hashlib
import json
import shlex
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from openqilin.control_plane.identity.connector_security import sign_payload_hash


@dataclass(frozen=True, slots=True)
class ParsedDiscordCommand:
    """Normalized command extracted from one Discord message."""

    action: str
    target: str | None
    args: tuple[str, ...]
    recipients: tuple[tuple[str, str], ...]
    project_id: str | None
    priority: str


class DiscordCommandParseError(ValueError):
    """Raised when a Discord command cannot be parsed safely."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _serialize_for_hash(data: Mapping[str, object]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def infer_command_target(action: str, explicit_target: str | None = None) -> str:
    """Resolve execution target from action prefix when target is omitted."""

    if explicit_target is not None and explicit_target.strip():
        return explicit_target.strip()
    normalized_action = action.strip().lower()
    if normalized_action.startswith("llm_"):
        return "llm"
    if normalized_action.startswith("msg_"):
        return "communication"
    return "sandbox"


def parse_discord_command(content: str, *, command_prefix: str) -> ParsedDiscordCommand | None:
    """Parse one Discord message into normalized command payload."""

    stripped = content.strip()
    if not stripped.startswith(command_prefix):
        return None
    body = stripped[len(command_prefix) :].strip()
    if not body:
        raise DiscordCommandParseError("command body is empty")
    if body.startswith("{"):
        try:
            data = json.loads(body)
        except json.JSONDecodeError as error:
            raise DiscordCommandParseError("invalid JSON command body") from error
        if not isinstance(data, dict):
            raise DiscordCommandParseError("JSON command body must be an object")
        action = str(data.get("action", "")).strip()
        if not action:
            raise DiscordCommandParseError("JSON command body requires action")
        explicit_target = data.get("target")
        target = str(explicit_target).strip() if explicit_target is not None else None
        raw_args = data.get("args", [])
        if not isinstance(raw_args, list):
            raise DiscordCommandParseError("JSON args must be a list")
        args = tuple(str(item) for item in raw_args)
        raw_recipients = data.get("recipients")
        recipients: tuple[tuple[str, str], ...]
        if raw_recipients is None:
            recipients = (("runtime", "runtime"),)
        else:
            if not isinstance(raw_recipients, list) or len(raw_recipients) == 0:
                raise DiscordCommandParseError("JSON recipients must be a non-empty list")
            normalized_recipients: list[tuple[str, str]] = []
            for recipient in raw_recipients:
                if not isinstance(recipient, dict):
                    raise DiscordCommandParseError("JSON recipient entries must be objects")
                recipient_id = str(recipient.get("recipient_id", "")).strip()
                recipient_type = str(recipient.get("recipient_type", "")).strip()
                if not recipient_id or not recipient_type:
                    raise DiscordCommandParseError(
                        "JSON recipient entries require recipient_id and recipient_type"
                    )
                normalized_recipients.append((recipient_id, recipient_type))
            recipients = tuple(normalized_recipients)
        project_id_value = data.get("project_id")
        project_id = str(project_id_value).strip() if project_id_value is not None else None
        priority_value = str(data.get("priority", "normal")).strip().lower() or "normal"
        return ParsedDiscordCommand(
            action=action,
            target=target,
            args=args,
            recipients=recipients,
            project_id=project_id or None,
            priority=priority_value,
        )

    tokens = shlex.split(body)
    if len(tokens) == 0:
        raise DiscordCommandParseError("command body is empty")
    action = tokens[0].strip()
    if not action:
        raise DiscordCommandParseError("action token is empty")
    args = tuple(token.strip() for token in tokens[1:] if token.strip())
    return ParsedDiscordCommand(
        action=action,
        target=None,
        args=args,
        recipients=(("runtime", "runtime"),),
        project_id=None,
        priority="normal",
    )


def build_discord_ingress_payload(
    *,
    parsed_command: ParsedDiscordCommand,
    message_id: str,
    actor_external_id: str,
    actor_role: str,
    content: str,
    guild_id: str,
    channel_id: str,
    channel_type: str,
    chat_class: str,
    connector_shared_secret: str,
    project_id: str | None = None,
    timestamp: datetime | None = None,
    bot_role: str | None = None,
    bot_id: str | None = None,
    bot_user_id: str | None = None,
    is_everyone_mention: bool = False,
) -> tuple[dict[str, object], str]:
    """Build signed payload for POST /v1/connectors/discord/messages."""

    normalized_timestamp = timestamp or datetime.now(tz=UTC)
    effective_project_id = project_id or parsed_command.project_id
    payload_without_hash: dict[str, object] = {
        "trace_id": f"trace-discord-{message_id}",
        "external_message_id": message_id,
        "actor_external_id": actor_external_id,
        "actor_role": actor_role,
        "idempotency_key": f"idem-discord-{message_id}",
        "timestamp": normalized_timestamp.isoformat(),
        "content": content,
        "action": parsed_command.action,
        "target": infer_command_target(parsed_command.action, parsed_command.target),
        "args": list(parsed_command.args),
        "recipients": [
            {"recipient_id": recipient_id, "recipient_type": recipient_type}
            for recipient_id, recipient_type in parsed_command.recipients
        ],
        "project_id": effective_project_id,
        "priority": parsed_command.priority,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "channel_type": channel_type,
        "chat_class": chat_class,
        "bot_role": bot_role,
        "bot_id": bot_id,
        "bot_user_id": bot_user_id,
        "is_everyone_mention": is_everyone_mention,
    }
    raw_payload_hash = hashlib.sha256(_serialize_for_hash(payload_without_hash)).hexdigest()
    payload = dict(payload_without_hash)
    payload["raw_payload_hash"] = raw_payload_hash
    signature = sign_payload_hash(raw_payload_hash, connector_shared_secret)
    return payload, f"sha256={signature}"


def format_governed_response(*, status_code: int, body: Mapping[str, object]) -> str:
    """Render one concise Discord response from governed API output."""

    trace_id = str(body.get("trace_id", "trace-unknown"))
    status_value = str(body.get("status", "unknown"))
    if status_value == "accepted":
        data = body.get("data")
        if isinstance(data, dict):
            task_id = str(data.get("task_id", "task-unknown"))
            command = str(data.get("command", "command-unknown"))
            replayed = str(data.get("replayed", "false"))
            summary = (
                f"[accepted] trace={trace_id} task={task_id} command={command} replayed={replayed}"
            )
            llm_execution = data.get("llm_execution")
            if isinstance(llm_execution, dict):
                generated_text = llm_execution.get("generated_text") or llm_execution.get(
                    "advisory_response"
                )
                if isinstance(generated_text, str) and generated_text.strip():
                    return generated_text.strip()
            return summary
        return f"[accepted] trace={trace_id}"
    if status_value in {"denied", "error"}:
        error = body.get("error")
        if isinstance(error, dict):
            code = str(error.get("code", "unknown_error"))
            message = str(error.get("message", "request denied")).replace("\n", " ").strip()
            if len(message) > 180:
                message = f"{message[:177]}..."
            return f"[{status_value}] trace={trace_id} code={code} message={message}"
        return f"[{status_value}] trace={trace_id}"
    return f"[http_{status_code}] trace={trace_id} status={status_value}"


def parse_actor_role_map(raw_json: str) -> dict[str, str]:
    """Parse actor role override map from JSON string safely."""

    normalized = raw_json.strip()
    if not normalized:
        return {}
    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in decoded.items():
        user_id = str(key).strip()
        role = str(value).strip().lower()
        if user_id and role:
            result[user_id] = role
    return result


def build_trace_suffix() -> str:
    """Generate short deterministic-like suffix for local response correlation."""

    return str(uuid4())[:8]
