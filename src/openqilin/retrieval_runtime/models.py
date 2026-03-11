"""Retrieval runtime request/result models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RetrievalDecision = Literal["ok", "denied"]


@dataclass(frozen=True, slots=True)
class RetrievalQueryRequest:
    """Canonical retrieval query request."""

    project_id: str
    query: str
    limit: int
    artifact_type: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalArtifactHit:
    """Normalized retrieval hit payload."""

    project_id: str
    artifact_id: str
    artifact_type: str
    title: str
    snippet: str
    source_ref: str
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalQueryResult:
    """Retrieval decision/result returned to control-plane query contract."""

    decision: RetrievalDecision
    hits: tuple[RetrievalArtifactHit, ...]
    error_code: str | None
    message: str
    retryable: bool


class RetrievalRuntimeError(RuntimeError):
    """Deterministic retrieval runtime error model."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
