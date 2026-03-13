from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping
from uuid import uuid4

from openqilin.control_plane.identity.connector_security import sign_payload_hash
from openqilin.shared_kernel.config import RuntimeSettings


def _serialize_for_hash(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def build_governance_headers(
    *,
    payload: Mapping[str, Any],
    actor_id: str,
    actor_role: str,
    channel: str = "discord",
    idempotency_key: str | None = None,
) -> dict[str, str]:
    raw_payload_hash = hashlib.sha256(_serialize_for_hash(payload)).hexdigest()
    idempotency_value = idempotency_key or f"idem-governance-{uuid4()}"
    signature = sign_payload_hash(raw_payload_hash, RuntimeSettings().connector_shared_secret)
    return {
        "X-External-Channel": channel,
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Actor-External-Id": actor_id,
        "X-OpenQilin-Actor-Role": actor_role,
        "X-Idempotency-Key": idempotency_value,
        "X-OpenQilin-Raw-Payload-Hash": raw_payload_hash,
        "X-OpenQilin-Signature": f"sha256={signature}",
    }
