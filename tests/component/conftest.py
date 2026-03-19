"""Component-test conftest: patch ``build_runtime_services`` with in-memory stubs.

All component tests that call ``create_control_plane_app()`` need a working
``RuntimeServices`` container.  Production ``build_runtime_services()`` requires
PostgreSQL, Redis and OPA — which are not available without the compose stack.

This conftest auto-uses the ``patch_build_runtime_services`` fixture so every
component test gets a fully-wired in-memory app without touching infra.
"""

from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

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
from openqilin.budget_runtime.client import AlwaysAllowBudgetRuntimeClient
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.communication_gateway.callbacks.outcome_notifier import (
    CommunicationOutcomeNotifier,
)
from openqilin.control_plane.api.dependencies import RuntimeServices
from openqilin.control_plane.api.startup_recovery import StartupRecoveryReport
from openqilin.control_plane.grammar.command_parser import CommandParser
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.intent_classifier import IntentClassifier
from openqilin.control_plane.idempotency.ingress_dedupe import IngressDedupeStore
from openqilin.data_access.artifact_file_store import ArtifactFileStore
from openqilin.data_access.repositories.task_execution_results import (
    InProcessTaskExecutionResultsRepository,
)
from openqilin.observability.testing.stubs import (
    InMemoryAuditWriter,
    InMemoryMetricRecorder,
    InMemoryTracer,
)
from openqilin.policy_runtime_integration.testing.in_memory_client import (
    InMemoryPolicyRuntimeClient,
)
from openqilin.retrieval_runtime.models import (
    RetrievalArtifactHit,
    RetrievalQueryRequest,
    RetrievalRuntimeError,
)
from openqilin.retrieval_runtime.service import RetrievalQueryService
from openqilin.task_orchestrator.admission.service import AdmissionService
from openqilin.task_orchestrator.callbacks.delivery_events import (
    LocalDeliveryEventCallbackProcessor,
)
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import build_task_dispatch_service
from openqilin.project_spaces.routing_resolver import ProjectSpaceRoutingResolver
from tests.testing.infra_stubs import (
    InMemoryAgentRegistryRepository,
    InMemoryCommunicationRepository,
    InMemoryGovernanceRepository,
    InMemoryIdentityChannelRepository,
    InMemoryIdempotencyCacheStore,
    InMemoryProjectArtifactRepository,
    InMemoryProjectSpaceBindingRepository,
    InMemoryRuntimeStateRepository,
)


_SEED_RETRIEVAL_HITS: tuple[RetrievalArtifactHit, ...] = tuple(
    RetrievalArtifactHit(
        project_id=f"project_{i}",
        artifact_id=f"artifact_{i}_001",
        artifact_type="project_charter",
        title=f"Project {i} Charter",
        snippet=f"retrieval status rollout project {i}",
        source_ref=f"projects/project_{i}/docs/project_charter--v001.md",
        score=0.95,
    )
    for i in range(1, 5)
)


class _SimulatedRetrievalReadModel:
    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        if "retrieval_error" in request.query:
            raise RetrievalRuntimeError(
                code="retrieval_backend_unavailable",
                message="simulated retrieval backend error",
                retryable=True,
            )
        return tuple(h for h in _SEED_RETRIEVAL_HITS if h.project_id == request.project_id)


def _build_test_runtime_services() -> RuntimeServices:
    """Build a fully-wired RuntimeServices using in-memory test stubs."""

    artifact_file_store = ArtifactFileStore(system_root=Path(tempfile.mkdtemp()))
    runtime_state_repo = InMemoryRuntimeStateRepository()
    communication_repo = InMemoryCommunicationRepository()
    agent_registry_repo = InMemoryAgentRegistryRepository()
    identity_channel_repo = InMemoryIdentityChannelRepository()
    project_artifact_repo = InMemoryProjectArtifactRepository()
    governance_repo = InMemoryGovernanceRepository()

    idempotency_cache_store = InMemoryIdempotencyCacheStore()
    ingress_dedupe = IngressDedupeStore()
    project_space_binding_repo = InMemoryProjectSpaceBindingRepository()
    routing_resolver = ProjectSpaceRoutingResolver(binding_repo=project_space_binding_repo)  # type: ignore[arg-type]

    llm_gateway = MagicMock()
    grammar_classifier = IntentClassifier(llm_gateway=llm_gateway)
    grammar_parser = CommandParser()
    grammar_router = FreeTextRouter()
    secretary_data_access = SecretaryDataAccessService(
        governance_repo=governance_repo,  # type: ignore[arg-type]
        runtime_state_repo=runtime_state_repo,
    )
    secretary_agent = SecretaryAgent(llm_gateway=llm_gateway, data_access=secretary_data_access)
    domain_leader_agent = DomainLeaderAgent(llm_gateway=llm_gateway)
    policy_runtime_client = InMemoryPolicyRuntimeClient()
    cso_agent = CSOAgent(
        llm_gateway=llm_gateway,
        project_artifact_repo=project_artifact_repo,  # type: ignore[arg-type]
        governance_repo=governance_repo,  # type: ignore[arg-type]
    )
    ceo_agent = CeoAgent(
        llm_gateway=llm_gateway,
        decision_writer=CeoDecisionWriter(governance_repo=project_artifact_repo),
        governance_repo=project_artifact_repo,
        cso_agent=cso_agent,
    )
    cwo_agent = CwoAgent(
        llm_gateway=llm_gateway,
        cso_agent=cso_agent,
        ceo_agent=ceo_agent,
        workforce_initializer=WorkforceInitializer(
            governance_repo=project_artifact_repo,
            agent_registry_repo=agent_registry_repo,  # type: ignore[arg-type]
        ),
        governance_repo=project_artifact_repo,  # type: ignore[arg-type]
        data_access=secretary_data_access,
    )

    budget_runtime_client = AlwaysAllowBudgetRuntimeClient()
    budget_reservation_service = BudgetReservationService(client=budget_runtime_client)
    lifecycle_service = TaskLifecycleService(runtime_state_repo=runtime_state_repo)

    admission_service = AdmissionService(
        dedupe_store=ingress_dedupe,
        runtime_state_repo=runtime_state_repo,
    )

    tracer = InMemoryTracer()
    audit_writer: InMemoryAuditWriter = InMemoryAuditWriter()
    auditor_agent = AuditorAgent(
        enforcement=AuditorEnforcementService(
            lifecycle_service=lifecycle_service,
            governance_repo=project_artifact_repo,
            audit_writer=audit_writer,
            communication_repo=communication_repo,  # type: ignore[arg-type]
        ),
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
    )
    administrator_agent = AdministratorAgent(
        document_policy=DocumentPolicyEnforcer(
            governance_repo=project_artifact_repo,
            audit_writer=audit_writer,
            artifact_file_store=artifact_file_store,
        ),
        retention=RetentionEnforcer(
            governance_repo=project_artifact_repo,
            audit_writer=audit_writer,
        ),
        governance_repo=project_artifact_repo,
        agent_registry_repo=agent_registry_repo,  # type: ignore[arg-type]
        audit_writer=audit_writer,
    )
    task_execution_results_repo = InProcessTaskExecutionResultsRepository()
    specialist_agent = SpecialistAgent(
        executor=SpecialistTaskExecutor(),
        task_execution_results_repo=task_execution_results_repo,
        governance_repo=project_artifact_repo,
        audit_writer=audit_writer,
    )
    metric_recorder = InMemoryMetricRecorder()

    delivery_event_callback_processor = LocalDeliveryEventCallbackProcessor(
        runtime_state_repo=runtime_state_repo,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )
    communication_outcome_notifier = CommunicationOutcomeNotifier(
        callback_processor=delivery_event_callback_processor
    )

    retrieval_query_service = RetrievalQueryService(read_model=_SimulatedRetrievalReadModel())

    task_dispatch_service = build_task_dispatch_service(
        lifecycle_service=lifecycle_service,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
        communication_repository=communication_repo,
        idempotency_cache_store=idempotency_cache_store,  # type: ignore[arg-type]
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
        artifact_writer=PMProjectArtifactWriter(project_artifact_repo=project_artifact_repo),
        data_access=secretary_data_access,
        domain_leader_agent=domain_leader_agent,
        task_dispatch_service=task_dispatch_service,  # type: ignore[arg-type]
        project_artifact_repo=project_artifact_repo,
    )

    startup_recovery_report = StartupRecoveryReport(
        restored_task_count=0,
        restored_terminal_task_count=0,
        reconstructed_ingress_claims=0,
        restored_communication_records=0,
        restored_dead_letter_count=0,
        restored_communication_idempotency_count=0,
        institutional_agent_count=0,
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
        idempotency_cache_store=idempotency_cache_store,  # type: ignore[arg-type]
        agent_registry_repo=agent_registry_repo,  # type: ignore[arg-type]
        identity_channel_repo=identity_channel_repo,  # type: ignore[arg-type]
        project_artifact_repo=project_artifact_repo,  # type: ignore[arg-type]
        governance_repo=governance_repo,  # type: ignore[arg-type]
        routing_resolver=routing_resolver,
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


@pytest.fixture(autouse=True)
def patch_build_runtime_services():
    """Replace build_runtime_services with test-stub factory for all component tests."""
    with patch(
        "openqilin.control_plane.api.app.build_runtime_services",
        side_effect=_build_test_runtime_services,
    ):
        yield
