"""Connector signature validation helpers for owner ingress."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from openqilin.shared_kernel.config import RuntimeSettings


class ConnectorSecurityError(ValueError):
    """Raised when connector authenticity checks fail."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ConnectorAuthContext:
    """Connector auth context resolved from headers and payload metadata."""

    channel: str
    actor_external_id: str
    idempotency_key: str
    raw_payload_hash: str


def _normalize_signature(signature: str) -> str:
    normalized = signature.strip()
    if normalized.startswith("sha256="):
        return normalized.split("=", 1)[1].strip()
    return normalized


def sign_payload_hash(raw_payload_hash: str, secret: str) -> str:
    """Create deterministic HMAC signature for connector payload hash."""

    return hmac.new(
        secret.encode("utf-8"),
        raw_payload_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_connector_auth(
    *,
    header_channel: str | None,
    header_actor_external_id: str | None,
    header_idempotency_key: str | None,
    header_signature: str | None,
    payload_channel: str,
    payload_actor_external_id: str,
    payload_idempotency_key: str,
    payload_raw_payload_hash: str,
) -> ConnectorAuthContext:
    """Validate connector metadata integrity and HMAC signature."""

    if header_signature is None or not header_signature.strip():
        raise ConnectorSecurityError(
            code="connector_signature_missing",
            message="missing required header: x-openqilin-signature",
        )

    if header_channel is not None and header_channel.strip() != payload_channel:
        raise ConnectorSecurityError(
            code="connector_channel_mismatch",
            message="connector channel header does not match payload connector channel",
        )
    if header_actor_external_id is not None and (
        header_actor_external_id.strip() != payload_actor_external_id
    ):
        raise ConnectorSecurityError(
            code="connector_actor_mismatch",
            message="connector actor header does not match payload actor_external_id",
        )
    if header_idempotency_key is not None and (
        header_idempotency_key.strip() != payload_idempotency_key
    ):
        raise ConnectorSecurityError(
            code="idempotency_key_mismatch",
            message="idempotency key header does not match payload connector metadata",
        )

    signature_value = _normalize_signature(header_signature)
    secret = RuntimeSettings().connector_shared_secret
    expected = sign_payload_hash(payload_raw_payload_hash, secret)
    if not hmac.compare_digest(signature_value, expected):
        raise ConnectorSecurityError(
            code="connector_signature_invalid",
            message="connector signature validation failed",
        )

    return ConnectorAuthContext(
        channel=payload_channel,
        actor_external_id=payload_actor_external_id,
        idempotency_key=payload_idempotency_key,
        raw_payload_hash=payload_raw_payload_hash,
    )
