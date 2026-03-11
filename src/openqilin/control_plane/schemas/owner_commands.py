"""Owner command transport schemas for governed ingress."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OwnerCommandRequest(BaseModel):
    """Owner-initiated command payload accepted by control-plane ingress."""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1, max_length=128)
    args: list[str] = Field(default_factory=list, max_length=32)
    metadata: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=128)


class OwnerCommandAcceptedResponse(BaseModel):
    """Response returned when ingress validation passes."""

    status: Literal["accepted"] = "accepted"
    task_id: str
    replayed: bool
    request_id: str
    trace_id: str
    principal_id: str
    connector: str
    command: str
    accepted_args: list[str]
    dispatch_target: str
    dispatch_id: str


class OwnerCommandRejectedResponse(BaseModel):
    """Response returned when ingress validation fails before admission."""

    status: Literal["blocked"] = "blocked"
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
