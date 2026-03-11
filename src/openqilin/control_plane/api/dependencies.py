"""Dependency providers for control-plane API."""

from __future__ import annotations

from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
from openqilin.task_orchestrator.admission.service import AdmissionService

_INGRESS_DEDUPE = InMemoryIngressDedupe()
_RUNTIME_STATE_REPO = InMemoryRuntimeStateRepository()
_ADMISSION_SERVICE = AdmissionService(
    dedupe_store=_INGRESS_DEDUPE,
    runtime_state_repo=_RUNTIME_STATE_REPO,
)
_POLICY_RUNTIME_CLIENT = InMemoryPolicyRuntimeClient()
_BUDGET_RUNTIME_CLIENT = InMemoryBudgetRuntimeClient()
_BUDGET_RESERVATION_SERVICE = BudgetReservationService(client=_BUDGET_RUNTIME_CLIENT)


def get_admission_service() -> AdmissionService:
    """Provide singleton admission service for API routes."""

    return _ADMISSION_SERVICE


def get_policy_runtime_client() -> InMemoryPolicyRuntimeClient:
    """Provide singleton policy-runtime client for API routes."""

    return _POLICY_RUNTIME_CLIENT


def get_budget_reservation_service() -> BudgetReservationService:
    """Provide singleton budget reservation service for API routes."""

    return _BUDGET_RESERVATION_SERVICE
