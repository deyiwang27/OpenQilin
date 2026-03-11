"""Runtime-state repository shell for task admission persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope


@dataclass(frozen=True, slots=True)
class TaskRecord:
    """Persisted task admission state."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    principal_role: str
    trust_domain: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    project_id: str | None
    idempotency_key: str
    status: str
    created_at: datetime
    outcome_source: str | None = None
    outcome_error_code: str | None = None
    outcome_message: str | None = None
    outcome_details: tuple[tuple[str, str], ...] | None = None
    dispatch_target: str | None = None
    dispatch_id: str | None = None


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
            principal_role=envelope.principal_role,
            trust_domain=envelope.trust_domain,
            connector=envelope.connector,
            command=envelope.command,
            target=envelope.target,
            args=envelope.args,
            metadata=envelope.metadata,
            project_id=envelope.project_id,
            idempotency_key=envelope.idempotency_key,
            status="queued",
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

    def update_task_status(
        self,
        task_id: str,
        status: str,
        *,
        outcome_source: str | None = None,
        outcome_error_code: str | None = None,
        outcome_message: str | None = None,
        outcome_details: Mapping[str, object] | None = None,
        dispatch_target: str | None = None,
        dispatch_id: str | None = None,
    ) -> TaskRecord | None:
        """Update persisted task status for downstream decision consistency."""

        task = self._task_by_id.get(task_id)
        if task is None:
            return None
        updated = replace(
            task,
            status=status,
            outcome_source=outcome_source if outcome_source is not None else task.outcome_source,
            outcome_error_code=(
                outcome_error_code if outcome_error_code is not None else task.outcome_error_code
            ),
            outcome_message=outcome_message
            if outcome_message is not None
            else task.outcome_message,
            outcome_details=(
                tuple(sorted((str(key), str(value)) for key, value in outcome_details.items()))
                if outcome_details is not None
                else task.outcome_details
            ),
            dispatch_target=dispatch_target
            if dispatch_target is not None
            else task.dispatch_target,
            dispatch_id=dispatch_id if dispatch_id is not None else task.dispatch_id,
        )
        self._task_by_id[task_id] = updated
        return updated
