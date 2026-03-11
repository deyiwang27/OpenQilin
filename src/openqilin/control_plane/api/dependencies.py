"""Dependency providers for control-plane API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Request

from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
from openqilin.task_orchestrator.admission.service import AdmissionService


@dataclass(slots=True)
class RuntimeServices:
    """Container for app-scoped runtime service instances."""

    ingress_dedupe: InMemoryIngressDedupe
    runtime_state_repo: InMemoryRuntimeStateRepository
    admission_service: AdmissionService
    policy_runtime_client: InMemoryPolicyRuntimeClient
    budget_runtime_client: InMemoryBudgetRuntimeClient
    budget_reservation_service: BudgetReservationService


def build_runtime_services() -> RuntimeServices:
    """Build a fresh runtime service container."""

    ingress_dedupe = InMemoryIngressDedupe()
    runtime_state_repo = InMemoryRuntimeStateRepository()
    admission_service = AdmissionService(
        dedupe_store=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
    )
    policy_runtime_client = InMemoryPolicyRuntimeClient()
    budget_runtime_client = InMemoryBudgetRuntimeClient()
    budget_reservation_service = BudgetReservationService(client=budget_runtime_client)
    return RuntimeServices(
        ingress_dedupe=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
        admission_service=admission_service,
        policy_runtime_client=policy_runtime_client,
        budget_runtime_client=budget_runtime_client,
        budget_reservation_service=budget_reservation_service,
    )


def get_runtime_services(request: Request) -> RuntimeServices:
    """Load runtime services from app state, initializing lazily if needed."""

    services = getattr(request.app.state, "runtime_services", None)
    if services is None:
        services = build_runtime_services()
        request.app.state.runtime_services = services
    return cast(RuntimeServices, services)


def get_admission_service(request: Request) -> AdmissionService:
    """Provide singleton admission service for API routes."""

    return get_runtime_services(request).admission_service


def get_policy_runtime_client(request: Request) -> InMemoryPolicyRuntimeClient:
    """Provide singleton policy-runtime client for API routes."""

    return get_runtime_services(request).policy_runtime_client


def get_budget_reservation_service(request: Request) -> BudgetReservationService:
    """Provide singleton budget reservation service for API routes."""

    return get_runtime_services(request).budget_reservation_service


def get_runtime_state_repository(request: Request) -> InMemoryRuntimeStateRepository:
    """Provide runtime-state repository for task status updates."""

    return get_runtime_services(request).runtime_state_repo
