# SEQ-0003: A2A + ACP Reliability Lifecycle

## Actors
- `task_orchestrator` (producer)
- `communication_gateway`
- `acp_runtime`
- `consumer_agent_runtime`
- `redis_idempotency_store`
- `dead_letter_ledger`

## Preconditions
- Message envelope includes:
  - `message_id`
  - `trace_id`
  - `idempotency_key`
  - policy and authority metadata
- Reliability profile v1 is active (`ack_deadline_ms=30000`, `max_attempts=3`).

## Sequence
```mermaid
sequenceDiagram
    autonumber
    participant PROD as task_orchestrator
    participant GW as communication_gateway
    participant ACP as acp_runtime
    participant CONS as consumer_agent_runtime
    participant REDIS as redis_idempotency_store
    participant DLQ as dead_letter_ledger

    PROD->>GW: publish(a2a envelope)
    GW->>ACP: send(frame attempt=1)
    ACP->>CONS: deliver(frame)
    CONS->>REDIS: setnx(channel+idempotency_key, ttl=72h)

    alt first-seen key
        CONS->>CONS: validate + authorize + execute side effects
        CONS-->>ACP: ack(processed)
        ACP-->>GW: success
        GW-->>PROD: delivery acked
    else duplicate key
        CONS-->>ACP: ack(processed)
        ACP-->>GW: duplicate consumed safely
        GW-->>PROD: delivery acked
    end

    alt retryable nack or ack timeout
        ACP->>ACP: retry with jittered backoff
        alt attempts exhausted
            ACP->>DLQ: append dead-letter(record + terminal code)
            ACP-->>GW: dead_lettered
            GW-->>PROD: dead_lettered
        end
    else non-retryable nack
        ACP->>DLQ: append dead-letter(record + terminal code)
        ACP-->>GW: dead_lettered
        GW-->>PROD: dead_lettered
    end
```

## Failure Branches
- Missing `idempotency_key`: non-retryable nack (`VALIDATION_FAILED`) -> dead-letter.
- Non-retryable authorization or schema failure: immediate dead-letter.
- Retryable transport failures: bounded retry then dead-letter on exhaustion.

## Expected Outputs
- Deterministic delivery outcomes (`acked` or `dead_lettered`).
- Immutable dead-letter records with trace and terminal error metadata.
- No duplicate side effects for duplicate deliveries.
