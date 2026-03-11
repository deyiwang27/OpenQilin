"""Query contract handler primitives."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.control_plane.schemas.queries import ArtifactSearchHit
from openqilin.retrieval_runtime.models import RetrievalQueryResult


@dataclass(frozen=True, slots=True)
class ArtifactSearchHandledResult:
    """Normalized query contract output for router response mapping."""

    status: str
    hits: list[ArtifactSearchHit]
    error_code: str | None
    message: str
    retryable: bool


def map_retrieval_result(result: RetrievalQueryResult) -> ArtifactSearchHandledResult:
    """Map retrieval runtime result into query contract payload shape."""

    if result.decision == "ok":
        return ArtifactSearchHandledResult(
            status="ok",
            hits=[
                ArtifactSearchHit(
                    artifact_id=hit.artifact_id,
                    artifact_type=hit.artifact_type,
                    title=hit.title,
                    snippet=hit.snippet,
                    source_ref=hit.source_ref,
                    score=hit.score,
                )
                for hit in result.hits
            ],
            error_code=None,
            message=result.message,
            retryable=False,
        )
    return ArtifactSearchHandledResult(
        status="denied",
        hits=[],
        error_code=result.error_code or "retrieval_query_denied",
        message=result.message,
        retryable=result.retryable,
    )
