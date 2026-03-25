from datetime import UTC, datetime

from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.control_plane.identity.connector_security import sign_payload_hash
from openqilin.shared_kernel.config import RuntimeSettings


def _discord_payload() -> dict[str, object]:
    return {
        "trace_id": "trace-m7-discord-adapter-001",
        "external_message_id": "discord-message-001",
        "actor_external_id": "owner_discord_001",
        "actor_role": "owner",
        "idempotency_key": "idem-m7-discord-adapter-001",
        "raw_payload_hash": "a" * 64,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "content": "Send update to ceo.",
        "action": "msg_notify",
        "args": ["ceo", "status_update"],
        "recipients": [{"recipient_id": "ceo_1", "recipient_type": "ceo"}],
        "priority": "normal",
        "guild_id": "guild-m7-discord-adapter",
        "channel_id": "dm-m7-discord-adapter",
        "channel_type": "dm",
        "chat_class": "direct",
    }


def test_discord_ingress_adapter_maps_payload_and_reuses_governed_owner_path() -> None:
    # M11: grammar layer classifies free-text content; action is intent-derived, not payload.action.
    # "Send update to ceo." stays neutral for Tier 1 routing → DISCUSSION (default) →
    # secretary bypass (direct channel).
    client = TestClient(create_control_plane_app())
    payload = _discord_payload()
    signature = sign_payload_hash(
        str(payload["raw_payload_hash"]),
        RuntimeSettings().connector_shared_secret,
    )

    response = client.post(
        "/v1/connectors/discord/messages",
        headers={"X-OpenQilin-Signature": f"sha256={signature}"},
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["connector"] == "discord"
    # M11: grammar layer routes free-text to secretary; command reflects intent class
    assert body["data"]["command"] == "discussion"
    assert body["data"]["dispatch_target"] == "secretary"


def test_discord_ingress_adapter_requires_signature_header() -> None:
    client = TestClient(create_control_plane_app())
    payload = _discord_payload()

    response = client.post(
        "/v1/connectors/discord/messages",
        json=payload,
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "connector_signature_missing"
