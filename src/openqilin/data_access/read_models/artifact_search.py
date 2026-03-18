"""Artifact search read-model baseline."""

from __future__ import annotations

from openqilin.retrieval_runtime.models import RetrievalArtifactHit, RetrievalQueryRequest


class LocalArtifactSearchReadModel:
    """No-op artifact search read model used until retrieval service is wired."""

    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        """Return empty result set (no retrieval backend configured)."""
        return ()


# Backward-compat alias
InMemoryArtifactSearchReadModel = LocalArtifactSearchReadModel
