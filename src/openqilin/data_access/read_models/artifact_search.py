"""Artifact search read-model baseline."""

from __future__ import annotations

from openqilin.retrieval_runtime.models import (
    RetrievalArtifactHit,
    RetrievalQueryRequest,
    RetrievalRuntimeError,
)


class LocalArtifactSearchReadModel:
    """No-op artifact search read model used until retrieval service is wired."""

    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        """Return empty result set (no retrieval backend configured).

        The special query string "retrieval_error" simulates a backend failure so that
        integration tests can exercise the fail-closed path without a live backend.
        """
        if request.query == "retrieval_error":
            raise RetrievalRuntimeError(
                code="retrieval_runtime_error_fail_closed",
                message="simulated retrieval backend error",
                retryable=True,
            )
        return ()


# Backward-compat alias
InMemoryArtifactSearchReadModel = LocalArtifactSearchReadModel
