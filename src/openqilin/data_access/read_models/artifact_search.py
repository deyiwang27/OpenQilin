"""Artifact search read-model baseline."""

from __future__ import annotations

from dataclasses import dataclass
import re

from openqilin.retrieval_runtime.models import (
    RetrievalArtifactHit,
    RetrievalQueryRequest,
    RetrievalRuntimeError,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True, slots=True)
class ArtifactSearchRecord:
    """In-memory artifact record for deterministic baseline retrieval."""

    project_id: str
    artifact_id: str
    artifact_type: str
    title: str
    content: str
    source_ref: str


class InMemoryArtifactSearchReadModel:
    """Simple scoped text-match retrieval baseline."""

    def __init__(self) -> None:
        self._records: tuple[ArtifactSearchRecord, ...] = (
            ArtifactSearchRecord(
                project_id="project_1",
                artifact_id="artifact_status_001",
                artifact_type="status_report",
                title="Project 1 M2 status report",
                content=(
                    "Milestone M2 tracks sandbox adapter, LiteLLM gateway, and "
                    "retrieval-backed query baseline rollout."
                ),
                source_ref="project_1/reports/m2_status.md",
            ),
            ArtifactSearchRecord(
                project_id="project_1",
                artifact_id="artifact_plan_001",
                artifact_type="execution_plan",
                title="Project 1 execution plan",
                content=(
                    "Execution plan includes work packages for retrieval path "
                    "validation and fail-closed handling."
                ),
                source_ref="project_1/plans/execution_plan.md",
            ),
            ArtifactSearchRecord(
                project_id="project_2",
                artifact_id="artifact_status_002",
                artifact_type="status_report",
                title="Project 2 retrospective",
                content="Legacy migration notes for unrelated project scope.",
                source_ref="project_2/reports/retro.md",
            ),
        )

    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        """Search artifacts in project scope with deterministic scoring."""

        query = request.query.strip().lower()
        if "retrieval_error" in query:
            raise RetrievalRuntimeError(
                code="retrieval_backend_unavailable",
                message="retrieval backend unavailable",
                retryable=True,
            )

        tokens = tuple(_TOKEN_PATTERN.findall(query))
        if not tokens:
            return ()

        ranked_hits: list[RetrievalArtifactHit] = []
        for record in self._records:
            if record.project_id != request.project_id:
                continue
            if request.artifact_type is not None and record.artifact_type != request.artifact_type:
                continue
            haystack = f"{record.title} {record.content}".lower()
            matched = sum(1 for token in tokens if token in haystack)
            if matched == 0:
                continue
            snippet = record.content[:160]
            score = round(matched / len(tokens), 3)
            ranked_hits.append(
                RetrievalArtifactHit(
                    project_id=record.project_id,
                    artifact_id=record.artifact_id,
                    artifact_type=record.artifact_type,
                    title=record.title,
                    snippet=snippet,
                    source_ref=record.source_ref,
                    score=score,
                )
            )

        ranked_hits.sort(key=lambda hit: (-hit.score, hit.artifact_id))
        return tuple(ranked_hits[: request.limit])
