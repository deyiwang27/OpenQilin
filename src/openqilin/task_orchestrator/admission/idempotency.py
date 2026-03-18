"""Admission idempotency coordination for replay-safe task creation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from openqilin.control_plane.idempotency.ingress_dedupe import IngressDedupeStore
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope


class AdmissionIdempotencyError(ValueError):
    """Raised when idempotency guarantees cannot be preserved."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class AdmissionIdempotencyOutcome:
    """Admission outcome after idempotency resolution."""

    task: TaskRecord
    replayed: bool


def _payload_hash(envelope: AdmissionEnvelope) -> str:
    raw = json.dumps(
        {
            "principal_id": envelope.principal_id,
            "connector": envelope.connector,
            "command": envelope.command,
            "args": list(envelope.args),
            "metadata": list(envelope.metadata),
            "idempotency_key": envelope.idempotency_key,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AdmissionIdempotencyCoordinator:
    """Coordinates dedupe claims and runtime-state idempotent task creation."""

    def __init__(
        self,
        dedupe_store: IngressDedupeStore,
        runtime_state_repo: PostgresTaskRepository,
    ) -> None:
        self._dedupe_store = dedupe_store
        self._runtime_state_repo = runtime_state_repo

    def resolve(self, envelope: AdmissionEnvelope) -> AdmissionIdempotencyOutcome:
        """Resolve admission request into new or replayed task deterministically."""

        hash_value = _payload_hash(envelope)
        claim_status, claim = self._dedupe_store.claim(
            principal_id=envelope.principal_id,
            idempotency_key=envelope.idempotency_key,
            payload_hash=hash_value,
        )

        if claim_status == "conflict":
            raise AdmissionIdempotencyError(
                code="idempotency_key_reused_with_different_payload",
                message=(
                    "idempotency key cannot be reused with a different payload "
                    f"for principal {envelope.principal_id}"
                ),
            )

        if claim_status == "replay":
            task = self._runtime_state_repo.get_task_by_principal_and_idempotency(
                principal_id=envelope.principal_id,
                idempotency_key=envelope.idempotency_key,
            )
            if task is None and claim.task_id is not None:
                task = self._runtime_state_repo.get_task_by_id(claim.task_id)
            if task is None:
                raise AdmissionIdempotencyError(
                    code="idempotency_state_missing",
                    message="existing idempotency claim has no recoverable task state",
                )
            return AdmissionIdempotencyOutcome(task=task, replayed=True)

        task = self._runtime_state_repo.create_task_from_envelope(envelope)
        self._dedupe_store.bind_task_id(
            principal_id=envelope.principal_id,
            idempotency_key=envelope.idempotency_key,
            task_id=task.task_id,
        )
        return AdmissionIdempotencyOutcome(task=task, replayed=False)
