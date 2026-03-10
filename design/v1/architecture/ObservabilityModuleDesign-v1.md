# OpenQilin v1 - Observability Module Design

## 1. Scope
- Translate the observability component design into implementation modules under `src/openqilin/observability/`.

## 2. Package Layout
```text
src/openqilin/observability/
  logging/
    logger.py
    context.py
  tracing/
    tracer.py
    spans.py
  metrics/
    recorder.py
  audit/
    audit_writer.py
    immutable_sink.py
  alerts/
    alert_emitter.py
  correlation/
    fields.py
    propagation.py
```

## 3. Key Interfaces
- `LoggerFactory.get(component_name)`
- `TraceContext.bind(correlation_fields)`
- `MetricRecorder.increment(name, tags)`
- `AuditWriter.append(event)`
- `AlertEmitter.emit(alert_event)`

## 4. Rules
- feature modules use observability facades instead of vendor SDKs directly
- `AuditWriter` is the only runtime path for immutable governance audit append
- correlation helpers enforce required fields before export or persistence
- observability export failures are fail-soft except when durable audit append is mandatory

## 5. Testing Focus
- correlation field completeness
- audit append durability semantics
- alert payload shaping
- structured log redaction and serialization
