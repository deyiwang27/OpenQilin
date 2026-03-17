"""PostgreSQL-backed runtime-state repository replacing InMemoryRuntimeStateRepository."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.state.transition_guard import assert_legal_transition


class PostgresTaskRepository:
    """PostgreSQL-backed runtime-state repository for task admission persistence."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO tasks (
                        task_id, request_id, trace_id, principal_id, principal_role,
                        trust_domain, connector, command, target, args, metadata,
                        project_id, idempotency_key, status, created_at
                    ) VALUES (
                        :task_id, :request_id, :trace_id, :principal_id, :principal_role,
                        :trust_domain, :connector, :command, :target, :args::jsonb, :metadata::jsonb,
                        :project_id, :idempotency_key, :status, :created_at
                    )
                    """
                ),
                _task_to_params(task),
            )
            session.commit()
        return task

    def get_task_by_id(self, task_id: str) -> TaskRecord | None:
        """Load task by task identifier."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text("SELECT * FROM tasks WHERE task_id = :task_id"),
                    {"task_id": task_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _task_from_row(dict(row))

    def get_task_by_principal_and_idempotency(
        self,
        principal_id: str,
        idempotency_key: str,
    ) -> TaskRecord | None:
        """Load task by principal plus idempotency key."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text(
                        """
                    SELECT * FROM tasks
                    WHERE principal_id = :principal_id
                      AND idempotency_key = :idempotency_key
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                    ),
                    {"principal_id": principal_id, "idempotency_key": idempotency_key},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _task_from_row(dict(row))

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

        existing = self.get_task_by_id(task_id)
        if existing is None:
            return None
        if existing.status != status:
            assert_legal_transition(existing.status, status)
        outcome_details_json: str | None = None
        if outcome_details is not None:
            outcome_details_json = json.dumps(
                sorted((str(k), str(v)) for k, v in outcome_details.items())
            )
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    UPDATE tasks SET
                        status              = :status,
                        outcome_source      = COALESCE(:outcome_source, outcome_source),
                        outcome_error_code  = COALESCE(:outcome_error_code, outcome_error_code),
                        outcome_message     = COALESCE(:outcome_message, outcome_message),
                        outcome_details     = CASE
                            WHEN :outcome_details IS NOT NULL
                            THEN :outcome_details::jsonb
                            ELSE outcome_details
                        END,
                        dispatch_target     = COALESCE(:dispatch_target, dispatch_target),
                        dispatch_id         = COALESCE(:dispatch_id, dispatch_id)
                    WHERE task_id = :task_id
                    """
                ),
                {
                    "task_id": task_id,
                    "status": status,
                    "outcome_source": outcome_source,
                    "outcome_error_code": outcome_error_code,
                    "outcome_message": outcome_message,
                    "outcome_details": outcome_details_json,
                    "dispatch_target": dispatch_target,
                    "dispatch_id": dispatch_id,
                },
            )
            session.commit()
        return self.get_task_by_id(task_id)

    def list_tasks(self) -> tuple[TaskRecord, ...]:
        """List all persisted tasks for diagnostics/startup recovery."""

        with self._session_factory() as session:
            rows = (
                session.execute(text("SELECT * FROM tasks ORDER BY created_at ASC"))
                .mappings()
                .all()
            )
        return tuple(_task_from_row(dict(row)) for row in rows)


def _task_to_params(task: TaskRecord) -> dict[str, object]:
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
        "args": json.dumps(list(task.args)),
        "metadata": json.dumps([list(item) for item in task.metadata]),
        "project_id": task.project_id,
        "idempotency_key": task.idempotency_key,
        "status": task.status,
        "created_at": task.created_at,
        "outcome_source": task.outcome_source,
        "outcome_error_code": task.outcome_error_code,
        "outcome_message": task.outcome_message,
        "outcome_details": (
            json.dumps([list(item) for item in task.outcome_details])
            if task.outcome_details
            else None
        ),
        "dispatch_target": task.dispatch_target,
        "dispatch_id": task.dispatch_id,
    }


def _task_from_row(row: dict[str, object]) -> TaskRecord:
    args_raw = row.get("args") or []
    if isinstance(args_raw, str):
        args_raw = json.loads(args_raw)
    metadata_raw = row.get("metadata") or []
    if isinstance(metadata_raw, str):
        metadata_raw = json.loads(metadata_raw)
    outcome_details_raw = row.get("outcome_details")
    if isinstance(outcome_details_raw, str):
        outcome_details_raw = json.loads(outcome_details_raw)
    created_at = row["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at).astimezone(UTC)
    elif hasattr(created_at, "tzinfo") and created_at.tzinfo is None:  # type: ignore[attr-defined]
        created_at = created_at.replace(tzinfo=UTC)  # type: ignore[attr-defined]
    return TaskRecord(
        task_id=str(row["task_id"]),
        request_id=str(row["request_id"]),
        trace_id=str(row["trace_id"]),
        principal_id=str(row["principal_id"]),
        principal_role=str(row["principal_role"]),
        trust_domain=str(row["trust_domain"]),
        connector=str(row["connector"]),
        command=str(row["command"]),
        target=str(row["target"]),
        args=tuple(str(item) for item in (args_raw if isinstance(args_raw, list) else [])),
        metadata=tuple(
            (str(item[0]), str(item[1]))
            for item in (metadata_raw if isinstance(metadata_raw, list) else [])
            if isinstance(item, (list, tuple)) and len(item) == 2
        ),
        project_id=str(row["project_id"]) if row.get("project_id") else None,
        idempotency_key=str(row["idempotency_key"]),
        status=str(row["status"]),
        created_at=created_at,  # type: ignore[arg-type]
        outcome_source=str(row["outcome_source"]) if row.get("outcome_source") else None,
        outcome_error_code=(
            str(row["outcome_error_code"]) if row.get("outcome_error_code") else None
        ),
        outcome_message=str(row["outcome_message"]) if row.get("outcome_message") else None,
        outcome_details=(
            tuple(
                (str(item[0]), str(item[1]))
                for item in (outcome_details_raw if isinstance(outcome_details_raw, list) else [])
                if isinstance(item, (list, tuple)) and len(item) == 2
            )
            or None
        )
        if outcome_details_raw
        else None,
        dispatch_target=str(row["dispatch_target"]) if row.get("dispatch_target") else None,
        dispatch_id=str(row["dispatch_id"]) if row.get("dispatch_id") else None,
    )
