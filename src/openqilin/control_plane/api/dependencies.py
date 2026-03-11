"""Dependency providers for control-plane API."""

from __future__ import annotations

from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.task_orchestrator.admission.service import AdmissionService

_INGRESS_DEDUPE = InMemoryIngressDedupe()
_RUNTIME_STATE_REPO = InMemoryRuntimeStateRepository()
_ADMISSION_SERVICE = AdmissionService(
    dedupe_store=_INGRESS_DEDUPE,
    runtime_state_repo=_RUNTIME_STATE_REPO,
)


def get_admission_service() -> AdmissionService:
    """Provide singleton admission service for API routes."""

    return _ADMISSION_SERVICE
