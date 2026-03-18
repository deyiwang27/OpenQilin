"""Ordering guards for communication delivery streams."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from openqilin.communication_gateway.validators.a2a_validator import A2AEnvelope


class OrderingValidationError(ValueError):
    """Raised when message ordering guarantees are violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LocalOrderingValidator:
    """Local in-process ordering and duplicate-id checks per communication stream."""

    def __init__(self) -> None:
        self._latest_seen_at_by_stream: dict[str, datetime] = {}
        self._message_ids_by_stream: dict[str, set[str]] = defaultdict(set)

    def validate(self, envelope: A2AEnvelope) -> None:
        """Validate stream ordering and duplicate message IDs."""

        stream_key = _stream_key(envelope)
        seen_message_ids = self._message_ids_by_stream[stream_key]
        if envelope.message_id in seen_message_ids:
            raise OrderingValidationError(
                code="a2a_duplicate_message_id",
                message="duplicate message_id detected in communication stream",
            )

        latest_seen_at = self._latest_seen_at_by_stream.get(stream_key)
        if latest_seen_at is not None and envelope.created_at < latest_seen_at:
            raise OrderingValidationError(
                code="a2a_out_of_order_delivery",
                message="message timestamp is older than latest stream message",
            )

        seen_message_ids.add(envelope.message_id)
        self._latest_seen_at_by_stream[stream_key] = envelope.created_at


def _stream_key(envelope: A2AEnvelope) -> str:
    project = envelope.project_id or "project-unspecified"
    return f"{envelope.connector}:{envelope.principal_id}:{project}:{envelope.target}"


# Backward-compatible alias retained for existing imports.
InMemoryOrderingValidator = LocalOrderingValidator
