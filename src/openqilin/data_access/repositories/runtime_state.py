"""Runtime-state repository shell for task admission persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from openqilin.shared_kernel.config import RuntimeSettings
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


class RuntimeStateRepositoryError(ValueError):
    """Raised when runtime-state snapshot persistence cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InMemoryRuntimeStateRepository:
    """In-memory runtime-state shell used for M1 admission and idempotency."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:
        self._task_by_id: dict[str, TaskRecord] = {}
        self._task_id_by_principal_key: dict[tuple[str, str], str] = {}
        self._snapshot_path = snapshot_path
        if self._snapshot_path is not None:
            self._load_snapshot()

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
        self._flush_snapshot()
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
        self._flush_snapshot()
        return updated

    def list_tasks(self) -> tuple[TaskRecord, ...]:
        """List all persisted tasks for diagnostics/startup recovery."""

        return tuple(self._task_by_id.values())

    def _load_snapshot(self) -> None:
        path = self._resolved_snapshot_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise RuntimeStateRepositoryError(
                code="runtime_state_snapshot_load_failed",
                message=f"failed to load runtime-state snapshot: {path}",
            ) from error
        records = payload.get("tasks", [])
        if not isinstance(records, list):
            raise RuntimeStateRepositoryError(
                code="runtime_state_snapshot_invalid",
                message="runtime-state snapshot tasks payload must be a list",
            )
        for raw in records:
            task = _task_from_dict(raw)
            self._task_by_id[task.task_id] = task
            self._task_id_by_principal_key[(task.principal_id, task.idempotency_key)] = task.task_id

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        path = self._resolved_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tasks": [_task_to_dict(task) for task in self._task_by_id.values()],
        }
        try:
            path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        except OSError as error:
            raise RuntimeStateRepositoryError(
                code="runtime_state_snapshot_write_failed",
                message=f"failed to write runtime-state snapshot: {path}",
            ) from error

    def _resolved_snapshot_path(self) -> Path:
        if self._snapshot_path is not None:
            return self._snapshot_path
        return RuntimeSettings().runtime_state_snapshot_path


def _task_to_dict(task: TaskRecord) -> dict[str, object]:
    return {
        "task_id": task.task_id,
        "request_id": task.request_id,
        "trace_id": task.trace_id,
        "principal_id": task.principal_id,
        "principal_role": task.principal_role,
        "trust_domain": task.trust_domain,
        "connector": task.connector,
        "command": task.command,
        "target": task.target,
        "args": list(task.args),
        "metadata": [list(item) for item in task.metadata],
        "project_id": task.project_id,
        "idempotency_key": task.idempotency_key,
        "status": task.status,
        "created_at": task.created_at.isoformat(),
        "outcome_source": task.outcome_source,
        "outcome_error_code": task.outcome_error_code,
        "outcome_message": task.outcome_message,
        "outcome_details": [list(item) for item in (task.outcome_details or ())],
        "dispatch_target": task.dispatch_target,
        "dispatch_id": task.dispatch_id,
    }


def _task_from_dict(raw: object) -> TaskRecord:
    if not isinstance(raw, dict):
        raise RuntimeStateRepositoryError(
            code="runtime_state_snapshot_invalid_record",
            message="runtime-state snapshot record must be an object",
        )
    metadata_raw = raw.get("metadata", [])
    outcome_details_raw = raw.get("outcome_details", [])
    return TaskRecord(
        task_id=str(raw["task_id"]),
        request_id=str(raw["request_id"]),
        trace_id=str(raw["trace_id"]),
        principal_id=str(raw["principal_id"]),
        principal_role=str(raw["principal_role"]),
        trust_domain=str(raw["trust_domain"]),
        connector=str(raw["connector"]),
        command=str(raw["command"]),
        target=str(raw["target"]),
        args=tuple(str(item) for item in metadata_or_list(raw.get("args", []))),
        metadata=tuple(
            (str(item[0]), str(item[1]))
            for item in metadata_or_list(metadata_raw)
            if isinstance(item, list) and len(item) == 2
        ),
        project_id=str(raw["project_id"]) if raw.get("project_id") is not None else None,
        idempotency_key=str(raw["idempotency_key"]),
        status=str(raw["status"]),
        created_at=datetime.fromisoformat(str(raw["created_at"])).astimezone(UTC),
        outcome_source=str(raw["outcome_source"])
        if raw.get("outcome_source") is not None
        else None,
        outcome_error_code=(
            str(raw["outcome_error_code"]) if raw.get("outcome_error_code") is not None else None
        ),
        outcome_message=str(raw["outcome_message"])
        if raw.get("outcome_message") is not None
        else None,
        outcome_details=tuple(
            (str(item[0]), str(item[1]))
            for item in metadata_or_list(outcome_details_raw)
            if isinstance(item, list) and len(item) == 2
        )
        or None,
        dispatch_target=str(raw["dispatch_target"])
        if raw.get("dispatch_target") is not None
        else None,
        dispatch_id=str(raw["dispatch_id"]) if raw.get("dispatch_id") is not None else None,
    )


def metadata_or_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []
