"""Dependency providers for control-plane API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Request

from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.communication_gateway.callbacks.outcome_notifier import CommunicationOutcomeNotifier
from openqilin.control_plane.api.startup_recovery import (
    StartupRecoveryReport,
    payload_hash_for_task,
)
from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.data_access.cache.idempotency_store import InMemoryIdempotencyCacheStore
from openqilin.data_access.repositories.agent_registry import (
    InMemoryAgentRegistryRepository,
)
from openqilin.data_access.repositories.artifacts import InMemoryProjectArtifactRepository
from openqilin.data_access.repositories.communication import InMemoryCommunicationRepository
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.data_access.repositories.identity_channels import (
    InMemoryIdentityChannelRepository,
)
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.observability.tracing.tracer import InMemoryTracer
from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
from openqilin.retrieval_runtime.service import (
    RetrievalQueryService,
    build_retrieval_query_service,
)
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.task_orchestrator.admission.service import AdmissionService
from openqilin.task_orchestrator.callbacks.delivery_events import (
    InMemoryDeliveryEventCallbackProcessor,
)
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import (
    TaskDispatchService,
    build_task_dispatch_service,
)


@dataclass(slots=True)
class RuntimeServices:
    """Container for app-scoped runtime service instances."""

    ingress_dedupe: InMemoryIngressDedupe
    runtime_state_repo: InMemoryRuntimeStateRepository
    communication_repo: InMemoryCommunicationRepository
    idempotency_cache_store: InMemoryIdempotencyCacheStore
    agent_registry_repo: InMemoryAgentRegistryRepository
    identity_channel_repo: InMemoryIdentityChannelRepository
    project_artifact_repo: InMemoryProjectArtifactRepository
    governance_repo: InMemoryGovernanceRepository
    admission_service: AdmissionService
    policy_runtime_client: InMemoryPolicyRuntimeClient
    budget_runtime_client: InMemoryBudgetRuntimeClient
    budget_reservation_service: BudgetReservationService
    lifecycle_service: TaskLifecycleService
    task_dispatch_service: TaskDispatchService
    retrieval_query_service: RetrievalQueryService
    tracer: InMemoryTracer
    audit_writer: InMemoryAuditWriter
    metric_recorder: InMemoryMetricRecorder
    delivery_event_callback_processor: InMemoryDeliveryEventCallbackProcessor
    communication_outcome_notifier: CommunicationOutcomeNotifier
    startup_recovery_report: StartupRecoveryReport


def build_runtime_services() -> RuntimeServices:
    """Build a fresh runtime service container."""

    settings = RuntimeSettings()
    runtime_snapshot_path = (
        settings.runtime_state_snapshot_path if settings.runtime_persistence_enabled else None
    )
    communication_snapshot_path = (
        settings.communication_snapshot_path if settings.runtime_persistence_enabled else None
    )
    idempotency_snapshot_path = (
        settings.idempotency_snapshot_path if settings.runtime_persistence_enabled else None
    )
    agent_registry_snapshot_path = (
        settings.agent_registry_snapshot_path if settings.runtime_persistence_enabled else None
    )
    ingress_dedupe = InMemoryIngressDedupe()
    runtime_state_repo = InMemoryRuntimeStateRepository(snapshot_path=runtime_snapshot_path)
    communication_repo = InMemoryCommunicationRepository(snapshot_path=communication_snapshot_path)
    idempotency_cache_store = InMemoryIdempotencyCacheStore(snapshot_path=idempotency_snapshot_path)
    agent_registry_repo = InMemoryAgentRegistryRepository(
        snapshot_path=agent_registry_snapshot_path
    )
    identity_channel_repo = InMemoryIdentityChannelRepository(
        snapshot_path=settings.identity_channel_snapshot_path
        if settings.runtime_persistence_enabled
        else None
    )
    project_artifact_repo = InMemoryProjectArtifactRepository(system_root=settings.system_root_path)
    governance_repo = InMemoryGovernanceRepository(artifact_repository=project_artifact_repo)
    admission_service = AdmissionService(
        dedupe_store=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
    )
    policy_runtime_client = InMemoryPolicyRuntimeClient()
    budget_runtime_client = InMemoryBudgetRuntimeClient()
    budget_reservation_service = BudgetReservationService(client=budget_runtime_client)
    lifecycle_service = TaskLifecycleService(runtime_state_repo=runtime_state_repo)
    retrieval_query_service = build_retrieval_query_service()
    tracer = InMemoryTracer()
    audit_writer = InMemoryAuditWriter()
    metric_recorder = InMemoryMetricRecorder()
    delivery_event_callback_processor = InMemoryDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_state_repo,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )
    communication_outcome_notifier = CommunicationOutcomeNotifier(
        callback_processor=delivery_event_callback_processor
    )
    task_dispatch_service = build_task_dispatch_service(
        lifecycle_service=lifecycle_service,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
        communication_repository=communication_repo,
        idempotency_cache_store=idempotency_cache_store,
        retrieval_query_service=retrieval_query_service,
        governance_project_reader=governance_repo,
    )
    reconstructed_ingress_claims = 0
    for task in runtime_state_repo.list_tasks():
        status, _ = ingress_dedupe.claim(
            principal_id=task.principal_id,
            idempotency_key=task.idempotency_key,
            payload_hash=payload_hash_for_task(task),
        )
        ingress_dedupe.bind_task_id(
            principal_id=task.principal_id,
            idempotency_key=task.idempotency_key,
            task_id=task.task_id,
        )
        if status == "new":
            reconstructed_ingress_claims += 1
    institutional_agents = agent_registry_repo.bootstrap_institutional_agents()
    startup_recovery_report = StartupRecoveryReport(
        restored_task_count=len(runtime_state_repo.list_tasks()),
        restored_terminal_task_count=sum(
            1
            for task in runtime_state_repo.list_tasks()
            if task.status in {"blocked", "dispatched", "completed", "failed", "cancelled"}
        ),
        reconstructed_ingress_claims=reconstructed_ingress_claims,
        restored_communication_records=len(
            task_dispatch_service.list_communication_message_records()
        ),
        restored_dead_letter_count=len(task_dispatch_service.list_communication_dead_letters()),
        restored_communication_idempotency_count=len(
            task_dispatch_service.list_communication_idempotency_records()
        ),
        institutional_agent_count=len(institutional_agents),
    )
    return RuntimeServices(
        ingress_dedupe=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
        communication_repo=communication_repo,
        idempotency_cache_store=idempotency_cache_store,
        agent_registry_repo=agent_registry_repo,
        identity_channel_repo=identity_channel_repo,
        project_artifact_repo=project_artifact_repo,
        governance_repo=governance_repo,
        admission_service=admission_service,
        policy_runtime_client=policy_runtime_client,
        budget_runtime_client=budget_runtime_client,
        budget_reservation_service=budget_reservation_service,
        lifecycle_service=lifecycle_service,
        task_dispatch_service=task_dispatch_service,
        retrieval_query_service=retrieval_query_service,
        tracer=tracer,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
        delivery_event_callback_processor=delivery_event_callback_processor,
        communication_outcome_notifier=communication_outcome_notifier,
        startup_recovery_report=startup_recovery_report,
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


def get_governance_repository(request: Request) -> InMemoryGovernanceRepository:
    """Provide governance repository for project lifecycle and proposal contracts."""

    return get_runtime_services(request).governance_repo


def get_identity_channel_repository(request: Request) -> InMemoryIdentityChannelRepository:
    """Provide connector identity/channel mapping repository for Discord ingress checks."""

    return get_runtime_services(request).identity_channel_repo


def get_task_dispatch_service(request: Request) -> TaskDispatchService:
    """Provide task-dispatch service for governed execution dispatch."""

    return get_runtime_services(request).task_dispatch_service


def get_retrieval_query_service(request: Request) -> RetrievalQueryService:
    """Provide retrieval query service for query contract endpoints."""

    return get_runtime_services(request).retrieval_query_service


def get_tracer(request: Request) -> InMemoryTracer:
    """Provide tracer for governed-path span emission."""

    return get_runtime_services(request).tracer


def get_audit_writer(request: Request) -> InMemoryAuditWriter:
    """Provide audit writer for governed-path decision evidence."""

    return get_runtime_services(request).audit_writer


def get_metric_recorder(request: Request) -> InMemoryMetricRecorder:
    """Provide metric recorder for governed-path counters."""

    return get_runtime_services(request).metric_recorder


def get_communication_outcome_notifier(request: Request) -> CommunicationOutcomeNotifier:
    """Provide communication outcome notifier for callback-driven lifecycle updates."""

    return get_runtime_services(request).communication_outcome_notifier
