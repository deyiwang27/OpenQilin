from __future__ import annotations

from pathlib import Path

from tests.testing.infra_stubs import InMemoryCommunicationRepository


def test_communication_repository_persists_records_and_dead_letters(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "system_root" / "runtime" / "communication.json"
    repository = InMemoryCommunicationRepository(snapshot_path=snapshot_path)

    prepared = repository.create_record(
        task_id="task-m7-wp1-001",
        trace_id="trace-m7-wp1-001",
        message_id="message-m7-wp1-001",
        external_message_id="external-m7-wp1-001",
        connector="discord",
        command="msg_notify",
        target="agent_runtime",
        route_key="discord.direct",
        endpoint="discord://channel/ops",
    )
    sent = repository.append_transition(
        prepared.ledger_id,
        state="sent",
        reason_code="acp_send_accepted",
        message="delivery accepted",
        retryable=None,
        dispatch_id="dispatch-m7-wp1-001",
        delivery_id="delivery-m7-wp1-001",
        error_code=None,
        error_message=None,
    )
    assert sent is not None
    dead_letter = repository.create_dead_letter_record(
        task_id="task-m7-wp1-001",
        trace_id="trace-m7-wp1-001",
        principal_id="owner_m7_001",
        idempotency_key="idem-m7-wp1-001",
        message_id="message-m7-wp1-001",
        external_message_id="external-m7-wp1-001",
        connector="discord",
        command="msg_notify",
        target="agent_runtime",
        route_key="discord.direct",
        endpoint="discord://channel/ops",
        error_code="communication_retry_exhausted",
        error_message="retry exhausted",
        attempts=3,
        ledger_id=prepared.ledger_id,
    )

    reloaded = InMemoryCommunicationRepository(snapshot_path=snapshot_path)
    restored = reloaded.get_record(prepared.ledger_id)
    assert restored is not None
    assert restored.state == "sent"
    assert restored.dispatch_id == "dispatch-m7-wp1-001"
    assert restored.delivery_id == "delivery-m7-wp1-001"
    dead_letters = reloaded.list_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].dead_letter_id == dead_letter.dead_letter_id
