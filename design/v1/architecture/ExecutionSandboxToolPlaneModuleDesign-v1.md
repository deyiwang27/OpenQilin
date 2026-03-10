# OpenQilin v1 - Execution Sandbox and Tool Plane Module Design

## 1. Scope
- Translate the sandbox/tool-plane component design into implementation modules under `src/openqilin/execution_sandbox/`.

## 2. Package Layout
```text
src/openqilin/execution_sandbox/
  runner/
    sandbox_runner.py
    process_runner.py
    quota_guard.py
  profiles/
    resolver.py
    enforcement.py
  tools/
    registry_resolver.py
    skill_binding_resolver.py
    invocation_adapter.py
  artifacts/
    capture.py
    redaction.py
  callbacks/
    event_publisher.py
```

## 3. Hosting Model
- v1 sandbox execution is hosted inside `orchestrator_worker`.
- isolation is process and profile based, not separate cluster-based scheduling.
- tool calls are always resolved through registry and skill bindings before invocation.

## 4. Key Interfaces
- `SandboxRunner.start(run_request)`
- `ProfileResolver.resolve(skill_id, tool_id, obligations)`
- `SkillBindingResolver.resolve(skill_id)`
- `InvocationAdapter.invoke(tool_request)`
- `ArtifactCapture.finalize(run_result)`

## 5. Enforcement Rules
- profile mismatch denies before process spawn
- egress is deny-by-default unless profile explicitly permits it
- output capture is redacted before persistence/export
- repeated containment events trigger escalation callback

## 6. Testing Focus
- profile enforcement
- denied tool binding paths
- quota breach containment
- artifact redaction and result capture
