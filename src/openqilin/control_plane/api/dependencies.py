"""Dependency providers for control-plane API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Request
from sqlalchemy.orm import sessionmaker

from openqilin.budget_runtime.client import PostgresBudgetRuntimeClient
from openqilin.budget_runtime.cost_evaluator import TokenCostEvaluator
from openqilin.budget_runtime.models import BudgetRuntimeClientProtocol
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.communication_gateway.callbacks.outcome_notifier import CommunicationOutcomeNotifier
from openqilin.control_plane.api.startup_recovery import (
    StartupRecoveryReport,
    payload_hash_for_task,
)
from openqilin.agents.administrator.agent import AdministratorAgent
from openqilin.agents.administrator.document_policy import DocumentPolicyEnforcer
from openqilin.agents.administrator.retention import RetentionEnforcer
from openqilin.agents.auditor.agent import AuditorAgent
from openqilin.agents.auditor.enforcement import AuditorEnforcementService
from openqilin.agents.ceo.agent import CeoAgent
from openqilin.agents.ceo.decision_writer import CeoDecisionWriter
from openqilin.agents.cso.agent import CSOAgent
from openqilin.agents.cwo.agent import CwoAgent
from openqilin.agents.cwo.workforce_initializer import WorkforceInitializer
from openqilin.agents.specialist.agent import SpecialistAgent
from openqilin.agents.specialist.task_executor import SpecialistTaskExecutor
from openqilin.agents.project_manager.agent import ProjectManagerAgent
from openqilin.agents.project_manager.artifact_writer import PMProjectArtifactWriter
from openqilin.agents.secretary.data_access import SecretaryDataAccessService
from openqilin.agents.domain_leader.agent import DomainLeaderAgent
from openqilin.agents.secretary.agent import SecretaryAgent
from openqilin.control_plane.grammar.command_parser import CommandParser
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.intent_classifier import IntentClassifier
from openqilin.control_plane.idempotency.ingress_dedupe import IngressDedupeStore
from openqilin.data_access.artifact_file_store import ArtifactFileStore
from openqilin.data_access.repositories.postgres.idempotency_cache_store import (
    RedisIdempotencyCacheStore,
    build_redis_client,
)
from openqilin.data_access.db.engine import create_sqlalchemy_engine
from openqilin.data_access.db.session import build_session_factory
from openqilin.data_access.repositories.postgres.agent_registry_repository import (
    PostgresAgentRegistryRepository,
)
from openqilin.data_access.repositories.postgres.communication_repository import (
    PostgresCommunicationRepository,
)
from openqilin.data_access.repositories.postgres.conversation_store import (
    PostgresConversationStore,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.data_access.repositories.postgres.budget_repository import (
    PostgresBudgetLedgerRepository,
)
from openqilin.data_access.repositories.postgres.identity_repository import (
    PostgresIdentityMappingRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import (
    PostgresProjectRepository,
)
from openqilin.data_access.repositories.postgres.audit_event_repository import (
    PostgresAuditEventRepository,
)
from openqilin.data_access.repositories.postgres.task_repository import (
    PostgresTaskRepository,
)
from openqilin.data_access.repositories.task_execution_results import (
    InProcessTaskExecutionResultsRepository,
)
from openqilin.observability.audit.audit_writer import OTelAuditWriter
from openqilin.observability.metrics.recorder import OTelMetricRecorder
from openqilin.observability.testing.stubs import (
    InMemoryAuditWriter,
    InMemoryMetricRecorder,
    InMemoryTracer,
)
from openqilin.policy_runtime_integration.client import (
    OPAPolicyRuntimeClient,
    PolicyRuntimeClient,
)
from openqilin.project_spaces.binding_repository import PostgresProjectSpaceBindingRepository
from openqilin.project_spaces.binding_service import ProjectSpaceBindingService
from openqilin.project_spaces.discord_automator import DiscordChannelAutomator
from openqilin.project_spaces.routing_resolver import ProjectSpaceRoutingResolver
from openqilin.discord_runtime.role_bot_registry import build_role_bot_registry
from openqilin.retrieval_runtime.service import (
    RetrievalQueryService,
    build_retrieval_query_service,
)
from openqilin.llm_gateway.service import LlmGatewayService, build_llm_gateway_service
from openqilin.shared_kernel.settings import get_settings
from openqilin.task_orchestrator.admission.service import AdmissionService
from openqilin.task_orchestrator.callbacks.delivery_events import (
    LocalDeliveryEventCallbackProcessor,
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
    project_manager_agent: ProjectManagerAgent
    cso_agent: CSOAgent
    ceo_agent: CeoAgent
    cwo_agent: CwoAgent
    auditor_agent: AuditorAgent
    administrator_agent: AdministratorAgent
    specialist_agent: SpecialistAgent
    task_execution_results_repo: InProcessTaskExecutionResultsRepository
    artifact_file_store: ArtifactFileStore
    domain_leader_agent: DomainLeaderAgent
    ingress_dedupe: IngressDedupeStore
    runtime_state_repo: PostgresTaskRepository
    communication_repo: PostgresCommunicationRepository
    ingress_idempotency_store: RedisIdempotencyCacheStore
    communication_idempotency_store: RedisIdempotencyCacheStore
    agent_registry_repo: PostgresAgentRegistryRepository
    identity_channel_repo: PostgresIdentityMappingRepository
    project_artifact_repo: PostgresGovernanceArtifactRepository
    governance_repo: PostgresProjectRepository
    admission_service: AdmissionService
    policy_runtime_client: PolicyRuntimeClient
    budget_runtime_client: BudgetRuntimeClientProtocol
    budget_reservation_service: BudgetReservationService
    lifecycle_service: TaskLifecycleService
    task_dispatch_service: TaskDispatchService
    retrieval_query_service: RetrievalQueryService
    tracer: InMemoryTracer
    audit_writer: InMemoryAuditWriter | OTelAuditWriter
    metric_recorder: InMemoryMetricRecorder | OTelMetricRecorder
    routing_resolver: ProjectSpaceRoutingResolver
    binding_service: ProjectSpaceBindingService
    delivery_event_callback_processor: LocalDeliveryEventCallbackProcessor
    communication_outcome_notifier: CommunicationOutcomeNotifier
    startup_recovery_report: StartupRecoveryReport


def build_runtime_services() -> RuntimeServices:
    """Build a fresh runtime service container.

    Called exactly once at application startup (stored in app.state.runtime_services).
    H-4 fix: lazy init removed from get_runtime_services(); this is the single init path.
    M13-WP9: fail-closed guards — all three infra URLs are required.
    """

    settings = get_settings()
    artifact_file_store = ArtifactFileStore(system_root=settings.system_root_path)

    if not settings.database_url:
        raise RuntimeError(
            "OPENQILIN_DATABASE_URL is required. Run: docker compose --profile core up -d"
        )
    if not settings.redis_url:
        raise RuntimeError(
            "OPENQILIN_REDIS_URL is required. Run: docker compose --profile core up -d"
        )
    if not settings.opa_url:
        raise RuntimeError(
            "OPENQILIN_OPA_URL is required. Run: docker compose --profile core up -d"
        )

    if settings.otlp_endpoint:
        metric_recorder: InMemoryMetricRecorder | OTelMetricRecorder = OTelMetricRecorder()
    else:
        metric_recorder = InMemoryMetricRecorder()

    llm_gateway: LlmGatewayService = build_llm_gateway_service()
    grammar_classifier = IntentClassifier(
        llm_gateway=llm_gateway,
        metric_recorder=metric_recorder,
    )
    grammar_parser = CommandParser()
    grammar_router = FreeTextRouter()
    domain_leader_agent = DomainLeaderAgent(llm_gateway=llm_gateway)

    # --- repository tier -------------------------------------------------
    engine = create_sqlalchemy_engine(settings.database_url)
    session_factory: sessionmaker = build_session_factory(engine)

    runtime_state_repo = PostgresTaskRepository(session_factory=session_factory)
    communication_repo = PostgresCommunicationRepository(session_factory=session_factory)
    agent_registry_repo = PostgresAgentRegistryRepository(session_factory=session_factory)
    identity_channel_repo = PostgresIdentityMappingRepository(session_factory=session_factory)
    project_artifact_repo = PostgresGovernanceArtifactRepository(
        session_factory=session_factory,
        artifact_file_store=artifact_file_store,
    )
    governance_repo = PostgresProjectRepository(session_factory=session_factory)
    audit_event_repo = PostgresAuditEventRepository(session_factory=session_factory)
    budget_ledger_repo = PostgresBudgetLedgerRepository(session_factory=session_factory)
    project_space_binding_repo = PostgresProjectSpaceBindingRepository(
        session_factory=session_factory
    )
    routing_resolver = ProjectSpaceRoutingResolver(binding_repo=project_space_binding_repo)
    try:
        _role_bot_registry = build_role_bot_registry(settings)
        _admin_identity = _role_bot_registry.identities_by_role.get("administrator")
        _channel_manager_token = (
            _admin_identity.token
            if _admin_identity is not None
            else (settings.discord_bot_token or "")
        )
    except Exception:
        _channel_manager_token = settings.discord_bot_token or ""
    discord_automator = DiscordChannelAutomator(
        bot_token=_channel_manager_token,
    )
    binding_service = ProjectSpaceBindingService(
        binding_repo=project_space_binding_repo,
        automator=discord_automator,
    )
    secretary_data_access = SecretaryDataAccessService(
        governance_repo=governance_repo,
        runtime_state_repo=runtime_state_repo,
    )
    artifact_writer = PMProjectArtifactWriter(project_artifact_repo=project_artifact_repo)

    # --- idempotency (Redis required) ------------------------------------
    redis_client = build_redis_client(settings.redis_url)
    ingress_idempotency_store = RedisIdempotencyCacheStore(
        client=redis_client,
        ttl_seconds=settings.idempotency_ttl_seconds,
        namespace="ingress",
    )
    communication_idempotency_store = RedisIdempotencyCacheStore(
        client=redis_client,
        ttl_seconds=settings.idempotency_ttl_seconds,
        namespace="communication",
    )

    ingress_dedupe = IngressDedupeStore()

    # --- services ----------------------------------------------------------------
    admission_service = AdmissionService(
        dedupe_store=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
    )
    policy_runtime_client: PolicyRuntimeClient = OPAPolicyRuntimeClient(opa_url=settings.opa_url)
    cso_agent = CSOAgent(
        llm_gateway=llm_gateway,
        project_artifact_repo=project_artifact_repo,
        governance_repo=governance_repo,
    )
    ceo_decision_writer = CeoDecisionWriter(governance_repo=project_artifact_repo)
    ceo_agent = CeoAgent(
        llm_gateway=llm_gateway,
        decision_writer=ceo_decision_writer,
        governance_repo=project_artifact_repo,
        cso_agent=cso_agent,
    )
    workforce_initializer = WorkforceInitializer(
        governance_repo=project_artifact_repo,
        agent_registry_repo=agent_registry_repo,
    )
    cwo_agent = CwoAgent(
        llm_gateway=llm_gateway,
        cso_agent=cso_agent,
        ceo_agent=ceo_agent,
        workforce_initializer=workforce_initializer,
        governance_repo=project_artifact_repo,
        data_access=secretary_data_access,
    )

    budget_ledger_repo.seed_default_allocation()
    budget_runtime_client = PostgresBudgetRuntimeClient(
        ledger_repo=budget_ledger_repo,
        cost_evaluator=TokenCostEvaluator(),
    )
    budget_reservation_service = BudgetReservationService(client=budget_runtime_client)
    lifecycle_service = TaskLifecycleService(runtime_state_repo=runtime_state_repo)
    retrieval_query_service = build_retrieval_query_service()
    conversation_store = (
        PostgresConversationStore(session_factory=session_factory, max_turns=40)
        if settings.runtime_persistence_enabled
        else None
    )
    secretary_agent = SecretaryAgent(
        llm_gateway=llm_gateway,
        data_access=secretary_data_access,
        conversation_store=conversation_store,
    )
    tracer = InMemoryTracer()
    # OTelAuditWriter with durable Postgres write (AUD-001).
    audit_writer: InMemoryAuditWriter | OTelAuditWriter = OTelAuditWriter(
        audit_repo=audit_event_repo
    )
    auditor_enforcement = AuditorEnforcementService(
        lifecycle_service=lifecycle_service,
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
        communication_repo=communication_repo,
    )
    auditor_agent = AuditorAgent(
        enforcement=auditor_enforcement,
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
    )
    document_policy_enforcer = DocumentPolicyEnforcer(
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
        artifact_file_store=artifact_file_store,
    )
    retention_enforcer = RetentionEnforcer(
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
    )
    administrator_agent = AdministratorAgent(
        document_policy=document_policy_enforcer,
        retention=retention_enforcer,
        governance_repo=project_artifact_repo,
        agent_registry_repo=agent_registry_repo,
        audit_writer=audit_writer,
    )
    task_execution_results_repo = InProcessTaskExecutionResultsRepository()
    specialist_agent = SpecialistAgent(
        executor=SpecialistTaskExecutor(),
        task_execution_results_repo=task_execution_results_repo,
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
    )
    delivery_event_callback_processor = LocalDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_state_repo,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )
    communication_outcome_notifier = CommunicationOutcomeNotifier(
        callback_processor=delivery_event_callback_processor
    )
    task_dispatch_service = build_task_dispatch_service(
        lifecycle_service=lifecycle_service,
        conversation_store=conversation_store,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
        communication_repository=communication_repo,
        retrieval_query_service=retrieval_query_service,
        governance_project_reader=governance_repo,
        governance_repository=governance_repo,
        project_artifact_repository=project_artifact_repo,
        runtime_state_repository=runtime_state_repo,
        budget_runtime_client=budget_runtime_client,
        specialist_agent=specialist_agent,
    )
    project_manager_agent = ProjectManagerAgent(
        llm_gateway=llm_gateway,
        artifact_writer=artifact_writer,
        data_access=secretary_data_access,
        domain_leader_agent=domain_leader_agent,
        task_dispatch_service=task_dispatch_service,
        project_artifact_repo=project_artifact_repo,
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
        project_manager_agent=project_manager_agent,
        cso_agent=cso_agent,
        ceo_agent=ceo_agent,
        cwo_agent=cwo_agent,
        auditor_agent=auditor_agent,
        administrator_agent=administrator_agent,
        specialist_agent=specialist_agent,
        task_execution_results_repo=task_execution_results_repo,
        artifact_file_store=artifact_file_store,
        domain_leader_agent=domain_leader_agent,
        ingress_dedupe=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
        communication_repo=communication_repo,
        ingress_idempotency_store=ingress_idempotency_store,
        communication_idempotency_store=communication_idempotency_store,
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
        routing_resolver=routing_resolver,
        binding_service=binding_service,
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
) -> PostgresTaskRepository:
    """Provide runtime-state repository for task status updates."""

    return get_runtime_services(request).runtime_state_repo


def get_governance_repository(
    request: Request,
) -> PostgresProjectRepository:
    """Provide governance repository for project lifecycle and proposal contracts."""

    return get_runtime_services(request).governance_repo


def get_identity_channel_repository(
    request: Request,
) -> PostgresIdentityMappingRepository:
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

    return get_runtime_services(request).tracer  # type: ignore[return-value]


def get_audit_writer(request: Request) -> InMemoryAuditWriter | OTelAuditWriter:
    """Provide audit writer for governed-path decision evidence."""

    return get_runtime_services(request).audit_writer


def get_metric_recorder(request: Request) -> InMemoryMetricRecorder | OTelMetricRecorder:
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


def get_project_manager_agent(request: Request) -> ProjectManagerAgent:
    """Provide Project Manager agent for project channel routing."""

    return get_runtime_services(request).project_manager_agent


def get_cso_agent(request: Request) -> CSOAgent:
    """Provide CSO governance advisory agent for institutional channel routing."""

    return get_runtime_services(request).cso_agent


def get_ceo_agent(request: Request) -> CeoAgent:
    """Provide CEO executive-decision agent for institutional routing."""

    return get_runtime_services(request).ceo_agent


def get_cwo_agent(request: Request) -> CwoAgent:
    """Provide CWO workforce-command agent for institutional routing."""

    return get_runtime_services(request).cwo_agent


def get_auditor_agent(request: Request) -> AuditorAgent:
    """Provide Auditor oversight agent for governance escalation paths."""

    return get_runtime_services(request).auditor_agent


def get_administrator_agent(request: Request) -> AdministratorAgent:
    """Provide Administrator enforcement agent for infrastructure control paths."""

    return get_runtime_services(request).administrator_agent


def get_specialist_agent(request: Request) -> SpecialistAgent:
    """Provide Specialist task-execution agent for PM dispatch paths."""

    return get_runtime_services(request).specialist_agent


def get_routing_resolver(request: Request) -> ProjectSpaceRoutingResolver:
    """Provide project space routing resolver for Discord channel → project context."""

    return get_runtime_services(request).routing_resolver


def get_binding_service(request: Request) -> ProjectSpaceBindingService:
    """Provide project space binding service for channel creation + binding persistence."""

    return get_runtime_services(request).binding_service


def get_domain_leader_agent(request: Request) -> DomainLeaderAgent:
    """Provide Domain Leader backend-routed virtual agent."""

    return get_runtime_services(request).domain_leader_agent
