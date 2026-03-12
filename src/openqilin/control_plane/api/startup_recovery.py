"""Runtime startup-recovery orchestration for persisted adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from openqilin.data_access.repositories.runtime_state import TaskRecord


@dataclass(frozen=True, slots=True)
class StartupRecoveryReport:
    """Summary of runtime startup-recovery actions."""

    restored_task_count: int
    restored_terminal_task_count: int
    reconstructed_ingress_claims: int
    restored_communication_records: int
    restored_dead_letter_count: int
    restored_communication_idempotency_count: int
    institutional_agent_count: int


def payload_hash_for_task(task: TaskRecord) -> str:
    """Rebuild admission idempotency payload hash from persisted task record."""

    raw = json.dumps(
        {
            "principal_id": task.principal_id,
            "connector": task.connector,
            "command": task.command,
            "args": list(task.args),
            "metadata": list(task.metadata),
            "idempotency_key": task.idempotency_key,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
