"""Ingress idempotency dedupe shell for owner command mutations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IngressDedupeRecord:
    """Stored dedupe claim for principal + idempotency key."""

    principal_id: str
    idempotency_key: str
    payload_hash: str
    task_id: str | None = None


class IngressDedupeStore:
    """Process-scoped dedupe store for command ingress replay safety."""

    def __init__(self) -> None:
        self._claims: dict[tuple[str, str], IngressDedupeRecord] = {}

    def claim(
        self,
        principal_id: str,
        idempotency_key: str,
        payload_hash: str,
    ) -> tuple[str, IngressDedupeRecord]:
        """Claim a key and detect replay/conflict.

        Returns status:
        - `new`: key was newly claimed.
        - `replay`: key already exists with same payload hash.
        - `conflict`: key exists with different payload hash.
        """

        claim_key = (principal_id, idempotency_key)
        existing = self._claims.get(claim_key)
        if existing is None:
            record = IngressDedupeRecord(
                principal_id=principal_id,
                idempotency_key=idempotency_key,
                payload_hash=payload_hash,
            )
            self._claims[claim_key] = record
            return "new", record

        if existing.payload_hash == payload_hash:
            return "replay", existing

        return "conflict", existing

    def bind_task_id(self, principal_id: str, idempotency_key: str, task_id: str) -> None:
        """Attach task id to an already-claimed dedupe record."""

        claim_key = (principal_id, idempotency_key)
        existing = self._claims.get(claim_key)
        if existing is None:
            return
        self._claims[claim_key] = IngressDedupeRecord(
            principal_id=existing.principal_id,
            idempotency_key=existing.idempotency_key,
            payload_hash=existing.payload_hash,
            task_id=task_id,
        )


# Backward-compat alias
InMemoryIngressDedupe = IngressDedupeStore
