# OpenQilin v1 - Communication Gateway Module Design

## 1. Scope
- Translate the communication gateway component design into implementation modules under `src/openqilin/communication_gateway/`.

## 2. Package Layout
```text
src/openqilin/communication_gateway/
  validators/
    a2a_validator.py
    ordering_validator.py
  transport/
    acp_client.py
    route_resolver.py
  delivery/
    publisher.py
    ack_handler.py
    retry_scheduler.py
    dlq_writer.py
  callbacks/
    outcome_notifier.py
  storage/
    message_ledger.py
    idempotency_store.py
```

## 3. Key Interfaces
- `Publisher.publish(envelope)`
- `A2AValidator.validate(envelope)`
- `AcpClient.send(frame)`
- `RetryScheduler.schedule(message_id, attempt)`
- `DlqWriter.write(message_id, terminal_code)`
- `OutcomeNotifier.notify(outcome)`

## 4. Ordering and Retry Rules
- ordering keys are computed before first persistence
- retries reuse the same logical message id and idempotency key
- `retry_scheduler` owns exponential backoff and attempt caps
- dead-letter persistence is terminal and immutable

## 5. Worker Ownership
- `communication_worker` hosts publish retries, ack handling, and dead-letter flow
- orchestrator interacts only through `Publisher` and delivery outcomes

## 6. Testing Focus
- A2A schema validation
- ordering-key derivation
- retry exhaustion and dead-letter transitions
- duplicate delivery acknowledgement safety
