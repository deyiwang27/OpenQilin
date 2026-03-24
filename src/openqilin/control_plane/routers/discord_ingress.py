"""Discord ingress adapter router mapping connector payloads to owner-command envelope."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

import structlog
import uuid

from openqilin.agents.administrator.agent import AdministratorAgent
from openqilin.agents.auditor.agent import AuditorAgent
from openqilin.agents.ceo.agent import CeoAgent
from openqilin.agents.cso.agent import CSOAgent
from openqilin.agents.cwo.agent import CwoAgent
from openqilin.agents.project_manager.agent import ProjectManagerAgent
from openqilin.agents.secretary.agent import SecretaryAgent
from openqilin.agents.secretary.models import SecretaryPolicyError, SecretaryRequest
from openqilin.agents.shared.free_text_advisory import FreeTextAdvisoryRequest
from openqilin.control_plane.identity.connector_security import (
    ConnectorSecurityError,
    validate_connector_auth,
)
from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.advisory.bot_registry_reader import BotRegistryReader
from openqilin.control_plane.advisory.channel_availability import (
    is_role_available_in_channel,
)
from openqilin.control_plane.advisory.topic_router import AdvisoryTopicRouter
from openqilin.control_plane.api.dependencies import (
    get_admission_service,
    get_advisory_topic_router,
    get_audit_writer,
    get_bot_registry_reader,
    get_budget_reservation_service,
    get_governance_repository,
    get_binding_service,
    get_grammar_classifier,
    get_grammar_parser,
    get_grammar_router,
    get_identity_channel_repository,
    get_administrator_agent,
    get_auditor_agent,
    get_ceo_agent,
    get_cso_agent,
    get_cwo_agent,
    get_metric_recorder,
    get_policy_runtime_client,
    get_project_manager_agent,
    get_routing_resolver,
    get_runtime_state_repository,
    get_secretary_agent,
    get_task_dispatch_service,
    get_tracer,
)
from openqilin.project_spaces.routing_resolver import ProjectSpaceRoutingResolver
from openqilin.control_plane.grammar.command_parser import CommandParser
from openqilin.control_plane.grammar.free_text_router import FreeTextRouter
from openqilin.control_plane.grammar.intent_classifier import IntentClassifier
from openqilin.control_plane.grammar.models import ChatContext, GrammarParseError
from openqilin.control_plane.routers.owner_commands import submit_owner_command
from openqilin.control_plane.schemas.discord_ingress import DiscordIngressRequest
from openqilin.control_plane.schemas.owner_commands import (
    OwnerCommandAcceptedData,
    OwnerCommandConnectorMetadata,
    OwnerCommandDiscordContext,
    OwnerCommandRequest,
    OwnerCommandResponse,
    OwnerCommandResolution,
    OwnerCommandSender,
)
from openqilin.data_access.repositories.postgres.identity_repository import (
    PostgresIdentityMappingRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import PostgresProjectRepository
from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
from openqilin.observability.testing.stubs import (
    InMemoryAuditWriter,
    InMemoryMetricRecorder,
    InMemoryTracer,
)
from openqilin.policy_runtime_integration.client import PolicyRuntimeClient
from openqilin.project_spaces.binding_service import ProjectSpaceBindingService
from openqilin.task_orchestrator.admission.service import AdmissionService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService

router = APIRouter(prefix="/v1/connectors/discord", tags=["discord_ingress"])
LOGGER = structlog.get_logger(__name__)

_COMMAND_PREFIX = "/oq"
_CONTEXT_FROM_PATTERN = re.compile(r"^/oq\s+context\s+from:#([a-z0-9_-]+)\s*$", re.IGNORECASE)
_ADVISORY_AGENT_ROLES = frozenset(
    {"ceo", "cwo", "auditor", "administrator", "cso", "project_manager"}
)


def _resolve_target(*, action: str, explicit_target: str | None) -> str:
    if explicit_target is not None and explicit_target.strip():
        return explicit_target.strip()
    normalized_action = action.strip().lower()
    if normalized_action.startswith("llm_"):
        return "llm"
    if normalized_action.startswith("msg_"):
        return "communication"
    return "sandbox"


def _grammar_error_response(
    payload: DiscordIngressRequest, error: GrammarParseError
) -> JSONResponse:
    """Convert GrammarParseError into a 400 validation_error JSON response."""
    return JSONResponse(
        status_code=400,
        content={
            "status": "denied",
            "trace_id": payload.trace_id,
            "error": {
                "code": error.code,
                "class": "validation_error",
                "message": error.message,
                "retryable": False,
                "source_component": "grammar_layer",
                "trace_id": payload.trace_id,
                "details": error.details,
            },
        },
    )


def _discord_advisory_response(
    *,
    payload: DiscordIngressRequest,
    command: str,
    message: str,
) -> OwnerCommandResponse:
    request_id = str(uuid.uuid4())
    return OwnerCommandResponse(
        status="accepted",
        trace_id=payload.trace_id,
        data=OwnerCommandAcceptedData(
            task_id=f"discord-context-{payload.external_message_id}",
            admission_state="dispatched",
            replayed=False,
            request_id=request_id,
            principal_id=payload.actor_external_id,
            connector="discord",
            command=command,
            accepted_args=[],
            dispatch_target="context_injection",
            llm_execution={"advisory_response": message},
        ),
    )


def _validate_discord_connector_request(
    *,
    payload: DiscordIngressRequest,
    signature_header: str | None,
) -> JSONResponse | None:
    try:
        validate_connector_auth(
            header_channel="discord",
            header_actor_external_id=payload.actor_external_id,
            header_idempotency_key=payload.idempotency_key,
            header_signature=signature_header,
            payload_channel="discord",
            payload_actor_external_id=payload.actor_external_id,
            payload_idempotency_key=payload.idempotency_key,
            payload_raw_payload_hash=payload.raw_payload_hash,
        )
    except ConnectorSecurityError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "trace_id": payload.trace_id,
                "error": {
                    "code": exc.code,
                    "class": "authorization_error",
                    "message": exc.message,
                    "retryable": False,
                    "source_component": "connector_security",
                    "trace_id": payload.trace_id,
                },
            },
        )
    return None


@router.post(
    "/messages",
    response_model=OwnerCommandResponse,
    status_code=202,
)
def submit_discord_message(
    payload: DiscordIngressRequest,
    request: Request,
    admission_service: AdmissionService = Depends(get_admission_service),
    policy_runtime_client: PolicyRuntimeClient = Depends(get_policy_runtime_client),
    budget_reservation_service: BudgetReservationService = Depends(get_budget_reservation_service),
    runtime_state_repo: PostgresTaskRepository = Depends(get_runtime_state_repository),
    task_dispatch_service: TaskDispatchService = Depends(get_task_dispatch_service),
    tracer: InMemoryTracer = Depends(get_tracer),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    metric_recorder: InMemoryMetricRecorder = Depends(get_metric_recorder),
    governance_repository: PostgresProjectRepository = Depends(get_governance_repository),
    identity_channel_repository: PostgresIdentityMappingRepository = Depends(
        get_identity_channel_repository
    ),
    binding_service: ProjectSpaceBindingService = Depends(get_binding_service),
    grammar_classifier: IntentClassifier = Depends(get_grammar_classifier),
    grammar_parser: CommandParser = Depends(get_grammar_parser),
    grammar_router: FreeTextRouter = Depends(get_grammar_router),
    secretary_agent: SecretaryAgent = Depends(get_secretary_agent),
    project_manager_agent: ProjectManagerAgent = Depends(get_project_manager_agent),
    cso_agent: CSOAgent = Depends(get_cso_agent),
    ceo_agent: CeoAgent = Depends(get_ceo_agent),
    cwo_agent: CwoAgent = Depends(get_cwo_agent),
    auditor_agent: AuditorAgent = Depends(get_auditor_agent),
    administrator_agent: AdministratorAgent = Depends(get_administrator_agent),
    routing_resolver: ProjectSpaceRoutingResolver = Depends(get_routing_resolver),
    advisory_topic_router: AdvisoryTopicRouter = Depends(get_advisory_topic_router),
    bot_registry_reader: BotRegistryReader = Depends(get_bot_registry_reader),
    x_openqilin_signature: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
) -> OwnerCommandResponse | JSONResponse:
    """Translate Discord connector payload into canonical owner-command ingress contract.

    Grammar layer is called before building the ingress payload:
    - Explicit /oq commands are parsed by CommandParser (bypasses free-text classifier).
    - Free-text messages are classified by IntentClassifier; mutation intent is rejected
      with GRAM-004 before reaching CommandHandler.
    - FreeTextRouter resolves the routing target for free-text discussion/query.
    - Free-text routed to secretary bypasses task dispatch; SecretaryAgent handles it directly.
    """
    # Resolve Discord channel to project context (M13-WP3).
    # If a binding exists and is active, use the DB-backed project_id and
    # default_recipient.  Unknown / inactive channels return None (fail-closed
    # at the resolver level); the payload's project_id is used as fallback.
    routing_context = routing_resolver.resolve(payload.guild_id, payload.channel_id)
    resolved_project_id = (
        routing_context.project_id if routing_context is not None else payload.project_id
    )

    grammar_context = ChatContext(
        chat_class=payload.chat_class,
        channel_id=payload.channel_id,
        project_id=resolved_project_id,
    )

    content = payload.content.strip()
    is_command = content.startswith(_COMMAND_PREFIX)
    _advisory_topic_router = (
        advisory_topic_router if hasattr(advisory_topic_router, "classify") else None
    )
    _bot_registry_reader = (
        bot_registry_reader if hasattr(bot_registry_reader, "get_mention") else None
    )

    if is_command:
        context_match = _CONTEXT_FROM_PATTERN.match(content)
        if context_match is not None:
            try:
                validate_connector_auth(
                    header_channel="discord",
                    header_actor_external_id=payload.actor_external_id,
                    header_idempotency_key=payload.idempotency_key,
                    header_signature=x_openqilin_signature,
                    payload_channel="discord",
                    payload_actor_external_id=payload.actor_external_id,
                    payload_idempotency_key=payload.idempotency_key,
                    payload_raw_payload_hash=payload.raw_payload_hash,
                )
            except ConnectorSecurityError as exc:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "trace_id": payload.trace_id,
                        "error": {
                            "code": exc.code,
                            "class": "authorization_error",
                            "message": exc.message,
                            "retryable": False,
                            "source_component": "connector_security",
                            "trace_id": payload.trace_id,
                        },
                    },
                )
            channel_name = context_match.group(1).lower()
            binding = binding_service.get_binding_by_name(channel_name, payload.guild_id)
            if binding is None:
                return _discord_advisory_response(
                    payload=payload,
                    command="context",
                    message=f"No project channel named #{channel_name} found.",
                )
            return _discord_advisory_response(
                payload=payload,
                command="context",
                message=(
                    f"Context from #{channel_name} noted. It will be included in your next message."
                ),
            )
        # Explicit /oq command: parse and derive action/target from grammar
        try:
            envelope = grammar_parser.parse(content)
        except GrammarParseError as exc:
            return _grammar_error_response(payload, exc)
        resolved_action = envelope.verb
        resolved_target = envelope.target or _resolve_target(
            action=payload.action, explicit_target=payload.target
        )
        resolved_args = [str(a) for a in envelope.args] if envelope.args else payload.args
        # /oq ask <agent_role> <text> — advisory shortcut bypassing governance pipeline
        _ALL_ADVISORY_ROLES = _ADVISORY_AGENT_ROLES | {"secretary"}
        if (
            resolved_action == "ask"
            and resolved_target is not None
            and resolved_target.lower() in _ALL_ADVISORY_ROLES
        ):
            auth_error = _validate_discord_connector_request(
                payload=payload,
                signature_header=x_openqilin_signature,
            )
            if auth_error is not None:
                return auth_error
            _ask_role = resolved_target.lower()
            _ask_text = " ".join(resolved_args).strip() if resolved_args else content
            if not _ask_text:
                _ask_text = content
            scope = f"guild::{payload.guild_id}::channel::{payload.channel_id}"
            if _ask_role == "secretary":
                try:
                    intent = grammar_classifier.classify(_ask_text, grammar_context)
                except GrammarParseError:
                    intent = grammar_classifier.classify("tell me about your role", grammar_context)
                sec_req = SecretaryRequest(
                    message=_ask_text,
                    intent=intent,
                    context=grammar_context,
                    trace_id=payload.trace_id,
                    channel_id=payload.channel_id,
                    guild_id=payload.guild_id,
                    actor_id=payload.actor_external_id,
                    addressed_agent="",
                )
                try:
                    sec_resp = secretary_agent.handle(sec_req)
                    _advisory_text = sec_resp.advisory_text
                except SecretaryPolicyError as exc:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "status": "denied",
                            "trace_id": payload.trace_id,
                            "error": {
                                "code": exc.code,
                                "class": "authorization_error",
                                "message": exc.message,
                                "retryable": False,
                                "source_component": "secretary_agent",
                                "trace_id": payload.trace_id,
                            },
                        },
                    )
                except Exception:
                    LOGGER.exception("discord_ingress.ask_advisory.secretary_failed")
                    _advisory_text = (
                        "I'm the Secretary agent. I'm unable to respond right now"
                        " — please try again."
                    )
                return _discord_advisory_response(
                    payload=payload, command="ask", message=_advisory_text
                )
            advisory_req = FreeTextAdvisoryRequest(
                text=_ask_text,
                scope=scope,
                guild_id=payload.guild_id,
                channel_id=payload.channel_id,
                addressed_agent=_ask_role,
            )
            try:
                if _ask_role == "ceo":
                    _resp = ceo_agent.handle_free_text(advisory_req)
                elif _ask_role == "cwo":
                    _resp = cwo_agent.handle_free_text(advisory_req)
                elif _ask_role == "auditor":
                    _resp = auditor_agent.handle_free_text(advisory_req)
                elif _ask_role == "administrator":
                    _resp = administrator_agent.handle_free_text(advisory_req)
                elif _ask_role == "cso":
                    _resp = cso_agent.handle_free_text(advisory_req)
                else:
                    _resp = project_manager_agent.handle_free_text(advisory_req)
                _advisory_text = _resp.advisory_text
            except Exception:
                LOGGER.exception("discord_ingress.ask_advisory.agent_failed", target_role=_ask_role)
                _advisory_text = (
                    f"I'm the {_ask_role.replace('_', ' ').title()} agent. "
                    "I'm unable to respond right now — please try again."
                )
            return _discord_advisory_response(
                payload=payload, command="ask", message=_advisory_text
            )
    else:
        # Free-text: classify intent, reject mutations, resolve routing target
        try:
            intent = grammar_classifier.classify(content, grammar_context)
        except GrammarParseError as exc:
            return _grammar_error_response(payload, exc)
        hint = grammar_router.resolve(intent, grammar_context)
        resolved_action = intent.value
        resolved_target = hint.target_role
        resolved_args = payload.args

        if payload.is_everyone_mention:
            auth_error = _validate_discord_connector_request(
                payload=payload,
                signature_header=x_openqilin_signature,
            )
            if auth_error is not None:
                return auth_error
            LOGGER.info("discord_ingress.everyone_broadcast", bot_role=payload.bot_role)
            if payload.bot_role == "secretary" or payload.bot_role is None:
                pass
            elif payload.bot_role in _ADVISORY_AGENT_ROLES:
                scope = f"guild::{payload.guild_id}::channel::{payload.channel_id}"
                advisory_request = FreeTextAdvisoryRequest(
                    text=content,
                    scope=scope,
                    guild_id=payload.guild_id,
                    channel_id=payload.channel_id,
                    addressed_agent=payload.bot_role,
                )
                try:
                    if payload.bot_role == "ceo":
                        advisory_response = ceo_agent.handle_free_text(advisory_request)
                    elif payload.bot_role == "cwo":
                        advisory_response = cwo_agent.handle_free_text(advisory_request)
                    elif payload.bot_role == "auditor":
                        advisory_response = auditor_agent.handle_free_text(advisory_request)
                    elif payload.bot_role == "administrator":
                        advisory_response = administrator_agent.handle_free_text(advisory_request)
                    elif payload.bot_role == "cso":
                        advisory_response = cso_agent.handle_free_text(advisory_request)
                    else:
                        advisory_response = project_manager_agent.handle_free_text(advisory_request)
                    advisory_text = advisory_response.advisory_text
                except Exception:
                    LOGGER.exception(
                        "discord_ingress.everyone_broadcast.agent_failed",
                        bot_role=payload.bot_role,
                    )
                    role_label = payload.bot_role.replace("_", " ").title()
                    advisory_text = (
                        f"I'm the {role_label} agent. "
                        "I'm unable to respond right now — please try again."
                    )
                return _discord_advisory_response(
                    payload=payload,
                    command="everyone_broadcast",
                    message=advisory_text,
                )

        # Advisory bypass: secretary handles discussion/query without task dispatch.
        # Validate connector signature first — bypass must not skip authenticity checks.
        if resolved_target == "secretary" and payload.bot_role not in _ADVISORY_AGENT_ROLES:
            auth_error = _validate_discord_connector_request(
                payload=payload,
                signature_header=x_openqilin_signature,
            )
            if auth_error is not None:
                return auth_error
            # Tier 1: deterministic advisory topic routing (M18-WP5)
            _tier1 = (
                _advisory_topic_router.classify(content)
                if _advisory_topic_router is not None
                else None
            )
            if _tier1 is not None:
                _is_project_channel = routing_context is not None
                if is_role_available_in_channel(_tier1.agent_role, _is_project_channel):
                    _scope = f"guild::{payload.guild_id}::channel::{payload.channel_id}"
                    _advisory_req = FreeTextAdvisoryRequest(
                        text=content,
                        scope=_scope,
                        guild_id=payload.guild_id,
                        channel_id=payload.channel_id,
                        addressed_agent=_tier1.agent_role,
                    )
                    try:
                        if _tier1.agent_role == "ceo":
                            _t1_resp = ceo_agent.handle_free_text(_advisory_req)
                        elif _tier1.agent_role == "cwo":
                            _t1_resp = cwo_agent.handle_free_text(_advisory_req)
                        elif _tier1.agent_role == "auditor":
                            _t1_resp = auditor_agent.handle_free_text(_advisory_req)
                        elif _tier1.agent_role == "cso":
                            _t1_resp = cso_agent.handle_free_text(_advisory_req)
                        elif _tier1.agent_role == "project_manager":
                            _t1_resp = project_manager_agent.handle_free_text(_advisory_req)
                        else:
                            _t1_resp = None
                        if _t1_resp is not None:
                            return _discord_advisory_response(
                                payload=payload,
                                command="ask",
                                message=_t1_resp.advisory_text,
                            )
                    except Exception:
                        LOGGER.exception(
                            "discord_ingress.tier1_routing.agent_failed",
                            target_role=_tier1.agent_role,
                        )
                        # Fall through to Secretary LLM on exception
                else:
                    # Role not available in this channel type — return referral message
                    _role_label = _tier1.agent_role.replace("_", " ").title()
                    _mention = (
                        _bot_registry_reader.get_mention(_tier1.agent_role)
                        if _bot_registry_reader is not None
                        else None
                    )
                    _mention_str = f" {_mention}" if _mention else ""
                    _referral_msg = (
                        f"The {_role_label} agent{_mention_str} is not available in project channels. "
                        f"Use `/oq ask {_tier1.agent_role} <your question>` in a general channel."
                    )
                    return _discord_advisory_response(
                        payload=payload,
                        command="ask",
                        message=_referral_msg,
                    )
            # Fall through: Tier 1 did not match or agent failed — Secretary LLM handles (Tier 2)
            _addressed_agent = ""
            for _r in payload.recipients:
                _rt = _r.recipient_type.strip().lower() if _r.recipient_type else ""
                if _rt and _rt not in ("runtime", "secretary", ""):
                    _addressed_agent = _rt
                    break

            sec_req = SecretaryRequest(
                message=content,
                intent=intent,
                context=grammar_context,
                trace_id=payload.trace_id,
                channel_id=payload.channel_id,
                guild_id=payload.guild_id,
                actor_id=payload.actor_external_id,
                addressed_agent=_addressed_agent,
            )
            try:
                sec_resp = secretary_agent.handle(sec_req)
            except SecretaryPolicyError as exc:
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "denied",
                        "trace_id": payload.trace_id,
                        "error": {
                            "code": exc.code,
                            "class": "authorization_error",
                            "message": exc.message,
                            "retryable": False,
                            "source_component": "secretary_agent",
                            "trace_id": payload.trace_id,
                        },
                    },
                )
            request_id = str(uuid.uuid4())
            return OwnerCommandResponse(
                status="accepted",
                trace_id=payload.trace_id,
                data=OwnerCommandAcceptedData(
                    task_id=f"secretary-{payload.external_message_id}",
                    admission_state="dispatched",
                    replayed=False,
                    request_id=request_id,
                    principal_id=payload.actor_external_id,
                    connector="discord",
                    command=resolved_action,
                    accepted_args=[],
                    dispatch_target="secretary",
                    llm_execution={
                        "advisory_response": sec_resp.advisory_text,
                        "routing_suggestion": sec_resp.routing_suggestion,
                    },
                ),
            )
        if payload.bot_role in _ADVISORY_AGENT_ROLES:
            auth_error = _validate_discord_connector_request(
                payload=payload,
                signature_header=x_openqilin_signature,
            )
            if auth_error is not None:
                return auth_error

            scope = f"guild::{payload.guild_id}::channel::{payload.channel_id}"
            advisory_request = FreeTextAdvisoryRequest(
                text=content,
                scope=scope,
                guild_id=payload.guild_id,
                channel_id=payload.channel_id,
                addressed_agent=payload.bot_role,
            )

            try:
                if payload.bot_role == "ceo":
                    advisory_response = ceo_agent.handle_free_text(advisory_request)
                elif payload.bot_role == "cwo":
                    advisory_response = cwo_agent.handle_free_text(advisory_request)
                elif payload.bot_role == "auditor":
                    advisory_response = auditor_agent.handle_free_text(advisory_request)
                elif payload.bot_role == "administrator":
                    advisory_response = administrator_agent.handle_free_text(advisory_request)
                elif payload.bot_role == "cso":
                    advisory_response = cso_agent.handle_free_text(advisory_request)
                else:
                    advisory_response = project_manager_agent.handle_free_text(advisory_request)
                advisory_text = advisory_response.advisory_text
            except Exception:
                LOGGER.exception(
                    "discord_ingress.advisory_bypass.failed", bot_role=payload.bot_role
                )
                advisory_text = (
                    f"I'm the {payload.bot_role.replace('_', ' ').title()} agent. "
                    "I'm unable to respond right now — please try again."
                )

            request_id = str(uuid.uuid4())
            return OwnerCommandResponse(
                status="accepted",
                trace_id=payload.trace_id,
                data=OwnerCommandAcceptedData(
                    task_id=f"{payload.bot_role}-{payload.external_message_id}",
                    admission_state="dispatched",
                    replayed=False,
                    request_id=request_id,
                    principal_id=payload.actor_external_id,
                    connector="discord",
                    command=resolved_action,
                    accepted_args=[],
                    dispatch_target=payload.bot_role,
                    llm_execution={
                        "advisory_response": advisory_text,
                        "routing_suggestion": None,
                    },
                ),
            )

    owner_payload = OwnerCommandRequest(
        message_id=payload.external_message_id,
        trace_id=payload.trace_id,
        sender=OwnerCommandSender(
            actor_id=payload.actor_external_id,
            actor_role=payload.actor_role,
        ),
        recipients=payload.recipients,
        message_type="command",
        priority=payload.priority,
        timestamp=payload.timestamp,
        content=payload.content,
        project_id=resolved_project_id,
        connector=OwnerCommandConnectorMetadata(
            channel="discord",
            external_message_id=payload.external_message_id,
            actor_external_id=payload.actor_external_id,
            idempotency_key=payload.idempotency_key,
            raw_payload_hash=payload.raw_payload_hash,
            discord_context=OwnerCommandDiscordContext(
                guild_id=payload.guild_id,
                channel_id=payload.channel_id,
                channel_type=payload.channel_type,
                chat_class=payload.chat_class,
                bot_role=payload.bot_role,
                bot_id=payload.bot_id,
                bot_user_id=payload.bot_user_id,
            ),
        ),
        command=OwnerCommandResolution(
            action=resolved_action,
            target=resolved_target,
            payload={"args": resolved_args},
        ),
    )
    return submit_owner_command(
        payload=owner_payload,
        request=request,
        admission_service=admission_service,
        tracer=tracer,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
        governance_repository=governance_repository,
        identity_channel_repository=identity_channel_repository,
        x_openqilin_trace_id=payload.trace_id,
        x_external_channel="discord",
        x_external_actor_id=payload.actor_external_id,
        x_idempotency_key=payload.idempotency_key,
        x_openqilin_signature=x_openqilin_signature,
    )
