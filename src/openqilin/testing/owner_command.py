from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Mapping
from uuid import uuid4

from openqilin.control_plane.identity.connector_security import sign_payload_hash
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRequest
from openqilin.shared_kernel.config import RuntimeSettings


def _serialize_for_hash(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def build_owner_command_request_dict(
    *,
    action: str,
    args: list[str] | None = None,
    actor_id: str,
    actor_role: str = "owner",
    idempotency_key: str | None = None,
    trace_id: str | None = None,
    project_id: str | None = "project_1",
    connector_channel: str = "discord",
    target: str = "sandbox",
    content: str = "owner command",
    recipients: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    args = args or []
    idempotency_key = idempotency_key or f"idem-test-{uuid4()}"
    trace_id = trace_id or f"trace-test-{uuid4()}"
    normalized_recipients = recipients or [{"recipient_id": "sandbox", "recipient_type": "runtime"}]
    core_payload: dict[str, Any] = {
        "message_id": f"msg-test-{uuid4()}",
        "trace_id": trace_id,
        "sender": {"actor_id": actor_id, "actor_role": actor_role},
        "recipients": normalized_recipients,
        "message_type": "command",
        "priority": "normal",
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "content": content,
        "project_id": project_id,
        "connector": {
            "channel": connector_channel,
            "external_message_id": f"ext-test-{uuid4()}",
            "actor_external_id": actor_id,
            "idempotency_key": idempotency_key,
        },
        "command": {
            "action": action,
            "target": target,
            "payload": {"args": args},
        },
    }
    raw_payload_hash = hashlib.sha256(_serialize_for_hash(core_payload)).hexdigest()
    connector = dict(core_payload["connector"])
    connector["raw_payload_hash"] = raw_payload_hash
    payload = dict(core_payload)
    payload["connector"] = connector
    return payload


def build_owner_command_request_model(**kwargs: Any) -> OwnerCommandRequest:
    return OwnerCommandRequest(**build_owner_command_request_dict(**kwargs))


def build_owner_command_headers(payload: dict[str, Any]) -> dict[str, str]:
    connector = payload["connector"]
    idempotency_key = str(connector["idempotency_key"])
    actor_external_id = str(connector["actor_external_id"])
    channel = str(connector["channel"])
    raw_payload_hash = str(connector["raw_payload_hash"])
    signature = sign_payload_hash(raw_payload_hash, RuntimeSettings().connector_shared_secret)
    return {
        "X-OpenQilin-Trace-Id": str(payload["trace_id"]),
        "X-External-Channel": channel,
        "X-External-Actor-Id": actor_external_id,
        "X-Idempotency-Key": idempotency_key,
        "X-OpenQilin-Signature": signature,
    }
