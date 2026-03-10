# OpenQilin v1 - Control Plane Module Design

## 1. Scope
- Translate the control-plane component design into implementation modules under `src/openqilin/control_plane/`.

## 2. Package Layout
```text
src/openqilin/control_plane/
  api/
    app.py
    dependencies.py
    middleware.py
    exception_handlers.py
  routers/
    owner_commands.py
    owner_discussions.py
    queries.py
    governance.py
  schemas/
    common.py
    owner_commands.py
    queries.py
    governance.py
  identity/
    connector_verifier.py
    principal_resolver.py
  handlers/
    command_handler.py
    query_handler.py
    governance_handler.py
  idempotency/
    ingress_dedupe.py
  presenters/
    response_mapper.py
    error_mapper.py
```

## 3. Runtime Responsibilities
- `routers`: HTTP binding only
- `schemas`: canonical transport validation and envelope models
- `identity`: Discord/external connector verification and principal binding
- `handlers`: orchestrator/query contract orchestration
- `idempotency`: header/body replay safety before mutation dispatch
- `presenters`: canonical response and error envelopes

## 4. Key Interfaces
- `CommandHandler.submit_owner_command(envelope, principal_ctx)`
- `QueryHandler.execute(contract_name, params, principal_ctx)`
- `GovernanceHandler.submit_action(action_request, principal_ctx)`
- `PrincipalResolver.resolve(external_identity)`
- `IngressDedupe.claim(idempotency_key, payload_hash)`

## 5. Dependency Rules
Allowed:
- `control_plane -> task_orchestrator`
- `control_plane -> policy_runtime_integration` for governed query checks only through service boundary
- `control_plane -> data_access` for read-model queries
- `control_plane -> observability`

Forbidden:
- direct `control_plane -> execution_sandbox`
- direct `control_plane -> llm_gateway`
- direct `control_plane -> communication_gateway`

## 6. Error and Response Mapping
- HTTP handlers never leak raw adapter exceptions.
- `error_mapper` converts internal failures to canonical code families.
- successful mutation responses always include `trace_id`, `status`, and policy metadata when applicable.

## 7. Testing Focus
- schema validation and canonical ingress envelope coverage
- identity verification and fail-closed paths
- idempotency duplicate-key behavior
- contract response/error mapping
