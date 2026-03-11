"""Query contract schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ArtifactSearchRequest(BaseModel):
    """Request payload for scoped artifact search contract."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    artifact_type: str | None = Field(default=None, min_length=1, max_length=64)


class ArtifactSearchHit(BaseModel):
    """Artifact search hit payload."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    artifact_type: str
    title: str
    snippet: str
    source_ref: str
    score: float


class QueryContractError(BaseModel):
    """Canonical query contract error payload."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool
    source_component: str
    details: dict[str, Any] = Field(default_factory=dict)


class QueryContractResponse(BaseModel):
    """Canonical query contract response envelope."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    contract_name: Literal["search_project_artifacts"]
    status: Literal["ok", "denied", "error"]
    policy_version: str | None = None
    policy_hash: str | None = None
    rule_ids: list[str] = Field(default_factory=list)
    data: dict[str, Any] | None = None
    error: QueryContractError | None = None
