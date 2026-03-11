"""Runtime-state repository shell for task admission persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope


@dataclass(frozen=True, slots=True)
class TaskRecord:
    """Persisted task admission state."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    connector: str
    command: str
    args: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    idempotency_key: str
    status: str
    created_at: datetime


class InMemoryRuntimeStateRepository:
    """In-memory runtime-state shell used for M1 admission and idempotency."""

    def __init__(self) -> None:
        self._task_by_id: dict[str, TaskRecord] = {}
        self._task_id_by_principal_key: dict[tuple[str, str], str] = {}

    def create_task_from_envelope(self, envelope: AdmissionEnvelope) -> TaskRecord:
        """Create and persist a new task record for admission envelope."""

        task = TaskRecord(
            task_id=str(uuid4()),
            request_id=envelope.request_id,
            trace_id=envelope.trace_id,
            principal_id=envelope.principal_id,
            connector=envelope.connector,
            command=envelope.command,
            args=envelope.args,
            metadata=envelope.metadata,
            idempotency_key=envelope.idempotency_key,
            status="admitted",
            created_at=datetime.now(tz=UTC),
        )
        self._task_by_id[task.task_id] = task
        self._task_id_by_principal_key[(task.principal_id, task.idempotency_key)] = task.task_id
        return task

    def get_task_by_id(self, task_id: str) -> TaskRecord | None:
        """Load task by task identifier."""

        return self._task_by_id.get(task_id)

    def get_task_by_principal_and_idempotency(
        self,
        principal_id: str,
        idempotency_key: str,
    ) -> TaskRecord | None:
        """Load task by principal plus idempotency key."""

        task_id = self._task_id_by_principal_key.get((principal_id, idempotency_key))
        if task_id is None:
            return None
        return self._task_by_id.get(task_id)

    def update_task_status(self, task_id: str, status: str) -> TaskRecord | None:
        """Update persisted task status for downstream decision consistency."""

        task = self._task_by_id.get(task_id)
        if task is None:
            return None
        updated = replace(task, status=status)
        self._task_by_id[task_id] = updated
        return updated
