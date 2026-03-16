"""Dependency providers for control-plane API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Request
from sqlalchemy.orm import sessionmaker

from openqilin.budget_runtime.client import InMemoryBudgetRuntimeClient
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.communication_gateway.callbacks.outcome_notifier import CommunicationOutcomeNotifier
from openqilin.control_plane.api.startup_recovery import (
    StartupRecoveryReport,
    payload_hash_for_task,
)
from openqilin.agents.secretary.agent import SecretaryAgent
from openqilin.control_plane.grammar.command_parser import CommandParser
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.intent_classifier import IntentClassifier
from openqilin.control_plane.idempotency.ingress_dedupe import InMemoryIngressDedupe
from openqilin.data_access.cache.idempotency_store import InMemoryIdempotencyCacheStore
from openqilin.data_access.repositories.postgres.idempotency_cache_store import (
    RedisIdempotencyCacheStore,
    build_redis_client,
)
from openqilin.data_access.db.engine import create_sqlalchemy_engine
from openqilin.data_access.db.session import build_session_factory
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
from openqilin.data_access.repositories.postgres.agent_registry_repository import (
    PostgresAgentRegistryRepository,
)
from openqilin.data_access.repositories.postgres.communication_repository import (
    PostgresCommunicationRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.data_access.repositories.postgres.identity_repository import (
    PostgresIdentityMappingRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import (
    PostgresProjectRepository,
)
from openqilin.data_access.repositories.postgres.task_repository import (
    PostgresTaskRepository,
)
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.observability.tracing.tracer import InMemoryTracer
from openqilin.policy_runtime_integration.client import (
    OPAPolicyRuntimeClient,
    PolicyRuntimeClient,
)
from openqilin.policy_runtime_integration.testing.in_memory_client import (
    InMemoryPolicyRuntimeClient,
)
from openqilin.retrieval_runtime.service import (
    RetrievalQueryService,
    build_retrieval_query_service,
)
from openqilin.llm_gateway.service import LlmGatewayService, build_llm_gateway_service
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

# Terminal task statuses for startup recovery counting (H-6: dispatched is NOT terminal).
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "blocked"})

# Statuses that hold an idempotency claim during startup recovery (H-5: only active tasks).
# blocked is included: task is alive and awaiting approval — must not allow duplicate submission.
_ACTIVE_STATUSES = frozenset({"queued", "dispatched", "running", "blocked"})


@dataclass(slots=True)
class RuntimeServices:
    """Container for app-scoped runtime service instances."""

    grammar_classifier: IntentClassifier
    grammar_parser: CommandParser
    grammar_router: FreeTextRouter
    secretary_agent: SecretaryAgent
    ingress_dedupe: InMemoryIngressDedupe
    runtime_state_repo: InMemoryRuntimeStateRepository | PostgresTaskRepository
    communication_repo: InMemoryCommunicationRepository | PostgresCommunicationRepository
    idempotency_cache_store: InMemoryIdempotencyCacheStore | RedisIdempotencyCacheStore
    agent_registry_repo: InMemoryAgentRegistryRepository | PostgresAgentRegistryRepository
    identity_channel_repo: InMemoryIdentityChannelRepository | PostgresIdentityMappingRepository
    project_artifact_repo: InMemoryProjectArtifactRepository | PostgresGovernanceArtifactRepository
    governance_repo: InMemoryGovernanceRepository | PostgresProjectRepository
    admission_service: AdmissionService
    policy_runtime_client: PolicyRuntimeClient
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
    """Build a fresh runtime service container.

    Called exactly once at application startup (stored in app.state.runtime_services).
    H-4 fix: lazy init removed from get_runtime_services(); this is the single init path.
    """

    settings = RuntimeSettings()
    llm_gateway: LlmGatewayService = build_llm_gateway_service()
    grammar_classifier = IntentClassifier(llm_gateway=llm_gateway)
    grammar_parser = CommandParser()
    grammar_router = FreeTextRouter()
    secretary_agent = SecretaryAgent(llm_gateway=llm_gateway)

    # --- repository tier selection -----------------------------------------
    # If database_url is set, use PostgreSQL-backed repositories.
    # Otherwise fall back to InMemory repositories (local dev / tests).

    if settings.database_url:
        engine = create_sqlalchemy_engine(settings.database_url)
        session_factory: sessionmaker = build_session_factory(engine)

        runtime_state_repo: InMemoryRuntimeStateRepository | PostgresTaskRepository = (
            PostgresTaskRepository(session_factory=session_factory)
        )
        communication_repo: InMemoryCommunicationRepository | PostgresCommunicationRepository = (
            PostgresCommunicationRepository(session_factory=session_factory)
        )
        agent_registry_repo: InMemoryAgentRegistryRepository | PostgresAgentRegistryRepository = (
            PostgresAgentRegistryRepository(session_factory=session_factory)
        )
        identity_channel_repo: (
            InMemoryIdentityChannelRepository | PostgresIdentityMappingRepository
        ) = PostgresIdentityMappingRepository(session_factory=session_factory)
        project_artifact_repo: (
            InMemoryProjectArtifactRepository | PostgresGovernanceArtifactRepository
        ) = PostgresGovernanceArtifactRepository(session_factory=session_factory)
        governance_repo: InMemoryGovernanceRepository | PostgresProjectRepository = (
            PostgresProjectRepository(session_factory=session_factory)
        )
    else:
        runtime_snapshot_path = (
            settings.runtime_state_snapshot_path if settings.runtime_persistence_enabled else None
        )
        communication_snapshot_path = (
            settings.communication_snapshot_path if settings.runtime_persistence_enabled else None
        )
        agent_registry_snapshot_path = (
            settings.agent_registry_snapshot_path if settings.runtime_persistence_enabled else None
        )
        identity_channel_snapshot_path = (
            settings.identity_channel_snapshot_path
            if settings.runtime_persistence_enabled
            else None
        )

        runtime_state_repo = InMemoryRuntimeStateRepository(snapshot_path=runtime_snapshot_path)
        communication_repo = InMemoryCommunicationRepository(
            snapshot_path=communication_snapshot_path
        )
        agent_registry_repo = InMemoryAgentRegistryRepository(
            snapshot_path=agent_registry_snapshot_path
        )
        identity_channel_repo = InMemoryIdentityChannelRepository(
            snapshot_path=identity_channel_snapshot_path
        )
        project_artifact_repo = InMemoryProjectArtifactRepository(
            system_root=settings.system_root_path
        )
        governance_repo = InMemoryGovernanceRepository(
            artifact_repository=project_artifact_repo  # type: ignore[arg-type]
        )

    # --- idempotency (M12-WP4: Redis when redis_url is set; InMemory otherwise) -
    idempotency_cache_store: InMemoryIdempotencyCacheStore | RedisIdempotencyCacheStore
    if settings.redis_url:
        idempotency_cache_store = RedisIdempotencyCacheStore(
            client=build_redis_client(settings.redis_url),
            ttl_seconds=settings.idempotency_ttl_seconds,
        )
    else:
        idempotency_snapshot_path = (
            settings.idempotency_snapshot_path if settings.runtime_persistence_enabled else None
        )
        idempotency_cache_store = InMemoryIdempotencyCacheStore(
            snapshot_path=idempotency_snapshot_path
        )

    ingress_dedupe = InMemoryIngressDedupe()

    # --- services ----------------------------------------------------------------
    admission_service = AdmissionService(
        dedupe_store=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
    )
    policy_runtime_client: PolicyRuntimeClient = (
        OPAPolicyRuntimeClient(opa_url=settings.opa_url)
        if settings.opa_url
        else InMemoryPolicyRuntimeClient()
    )
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
        governance_repository=governance_repo,
        project_artifact_repository=project_artifact_repo,
        runtime_state_repository=runtime_state_repo,
        budget_runtime_client=budget_runtime_client,
    )

    # --- startup recovery --------------------------------------------------------
    # H-5 fix: only re-claim tasks in active statuses (queued/dispatched/running).
    # H-6 fix: terminal count excludes dispatched.
    reconstructed_ingress_claims = 0
    for task in runtime_state_repo.list_tasks():
        if task.status in _ACTIVE_STATUSES:
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
            1 for task in runtime_state_repo.list_tasks() if task.status in _TERMINAL_STATUSES
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
        grammar_classifier=grammar_classifier,
        grammar_parser=grammar_parser,
        grammar_router=grammar_router,
        secretary_agent=secretary_agent,
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
    """Load runtime services from app state.

    H-4 fix: no lazy init fallback. Services must be pre-built in create_control_plane_app()
    and stored in app.state.runtime_services before any request is handled.
    """

    services = getattr(request.app.state, "runtime_services", None)
    if services is None:
        raise RuntimeError(
            "RuntimeServices not initialized. "
            "build_runtime_services() must be called before accepting requests."
        )
    return cast(RuntimeServices, services)


def get_admission_service(request: Request) -> AdmissionService:
    """Provide singleton admission service for API routes."""

    return get_runtime_services(request).admission_service


def get_policy_runtime_client(request: Request) -> PolicyRuntimeClient:
    """Provide singleton policy-runtime client for API routes."""

    return get_runtime_services(request).policy_runtime_client


def get_budget_reservation_service(request: Request) -> BudgetReservationService:
    """Provide singleton budget reservation service for API routes."""

    return get_runtime_services(request).budget_reservation_service


def get_runtime_state_repository(
    request: Request,
) -> InMemoryRuntimeStateRepository | PostgresTaskRepository:
    """Provide runtime-state repository for task status updates."""

    return get_runtime_services(request).runtime_state_repo


def get_governance_repository(
    request: Request,
) -> InMemoryGovernanceRepository | PostgresProjectRepository:
    """Provide governance repository for project lifecycle and proposal contracts."""

    return get_runtime_services(request).governance_repo


def get_identity_channel_repository(
    request: Request,
) -> InMemoryIdentityChannelRepository | PostgresIdentityMappingRepository:
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


def get_grammar_classifier(request: Request) -> IntentClassifier:
    """Provide grammar intent classifier for Discord ingress routing."""

    return get_runtime_services(request).grammar_classifier


def get_grammar_parser(request: Request) -> CommandParser:
    """Provide grammar command parser for /oq compact command syntax."""

    return get_runtime_services(request).grammar_parser


def get_grammar_router(request: Request) -> FreeTextRouter:
    """Provide grammar free-text router for intent-to-target resolution."""

    return get_runtime_services(request).grammar_router


def get_secretary_agent(request: Request) -> SecretaryAgent:
    """Provide Secretary advisory agent for institutional channel routing."""

    return get_runtime_services(request).secretary_agent
