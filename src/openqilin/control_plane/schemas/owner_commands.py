"""Owner command transport schemas for governed ingress."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OwnerCommandSender(BaseModel):
    """Sender descriptor for owner command envelope."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1, max_length=128)
    actor_role: str = Field(min_length=1, max_length=64)


class OwnerCommandRecipient(BaseModel):
    """Recipient descriptor for owner command envelope."""

    model_config = ConfigDict(extra="forbid")

    recipient_id: str = Field(min_length=1, max_length=128)
    recipient_type: str = Field(min_length=1, max_length=64)


class OwnerCommandConnectorMetadata(BaseModel):
    """Connector metadata required for ingress authenticity and replay control."""

    model_config = ConfigDict(extra="forbid")

    channel: Literal["discord", "internal"]
    external_message_id: str = Field(min_length=1, max_length=256)
    actor_external_id: str = Field(min_length=1, max_length=256)
    idempotency_key: str = Field(min_length=8, max_length=128)
    raw_payload_hash: str = Field(min_length=64, max_length=128)


class OwnerCommandResolution(BaseModel):
    """Resolved execution intent extracted from owner message."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


class OwnerCommandRequest(BaseModel):
    """Owner-initiated command payload accepted by control-plane ingress."""

    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(min_length=1, max_length=256)
    trace_id: str = Field(min_length=1, max_length=128)
    sender: OwnerCommandSender
    recipients: list[OwnerCommandRecipient] = Field(min_length=1, max_length=32)
    message_type: Literal["command"]
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    timestamp: datetime
    content: str = Field(min_length=1, max_length=4000)
    project_id: str | None = Field(default=None, min_length=1, max_length=128)
    connector: OwnerCommandConnectorMetadata
    command: OwnerCommandResolution


class OwnerCommandAcceptedData(BaseModel):
    """Accepted response data payload."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    admission_state: Literal["queued", "blocked", "dispatched"]
    replayed: bool
    request_id: str
    principal_id: str
    connector: str
    command: str
    accepted_args: list[str]
    dispatch_target: str | None = None
    dispatch_id: str | None = None


class OwnerCommandError(BaseModel):
    """Canonical runtime error envelope."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    code: str
    error_class: Literal[
        "validation_error",
        "authorization_error",
        "budget_error",
        "runtime_error",
        "safety_error",
    ] = Field(alias="class")
    message: str
    retryable: bool
    source_component: str
    trace_id: str
    policy_version: str | None = None
    policy_hash: str | None = None
    rule_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class OwnerCommandResponse(BaseModel):
    """Canonical owner-command response envelope."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted", "denied", "error"]
    trace_id: str
    policy_version: str | None = None
    policy_hash: str | None = None
    rule_ids: list[str] = Field(default_factory=list)
    data: OwnerCommandAcceptedData | None = None
    error: OwnerCommandError | None = None
