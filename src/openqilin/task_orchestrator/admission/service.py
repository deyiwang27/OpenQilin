"""Admission service shell for governed task creation."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.admission.idempotency import (
    AdmissionIdempotencyCoordinator,
    AdmissionIdempotencyError,
)


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """Result returned by admission service."""

    task: TaskRecord
    replayed: bool


class AdmissionService:
    """Coordinates task admission with idempotency and state persistence."""

    def __init__(
        self,
        dedupe_store: InMemoryIngressDedupe,
        runtime_state_repo: InMemoryRuntimeStateRepository,
    ) -> None:
        self._idempotency = AdmissionIdempotencyCoordinator(
            dedupe_store=dedupe_store,
            runtime_state_repo=runtime_state_repo,
        )

    def admit_owner_command(self, envelope: AdmissionEnvelope) -> AdmissionResult:
        """Create or replay admission task in an idempotent manner."""

        outcome = self._idempotency.resolve(envelope)
        return AdmissionResult(task=outcome.task, replayed=outcome.replayed)


__all__ = ["AdmissionIdempotencyError", "AdmissionResult", "AdmissionService"]
