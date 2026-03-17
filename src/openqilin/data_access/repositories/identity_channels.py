"""Connector identity/channel mapping repository for Discord ingress governance."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from openqilin.shared_kernel.config import RuntimeSettings

IdentityChannelStatus = Literal["pending", "verified", "revoked"]


@dataclass(frozen=True, slots=True)
class IdentityChannelMappingRecord:
    """Persisted connector actor<->channel mapping state."""

    mapping_id: str
    connector: str
    actor_external_id: str
    guild_id: str
    channel_id: str
    channel_type: str
    status: IdentityChannelStatus
    created_at: datetime
    updated_at: datetime
    principal_role: str = "owner"


class IdentityChannelRepositoryError(ValueError):
    """Raised when identity/channel repository contracts are violated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InMemoryIdentityChannelRepository:
    """In-memory identity/channel mapping repository with optional snapshots."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:
        self._records_by_id: dict[str, IdentityChannelMappingRecord] = {}
        self._mapping_id_by_key: dict[tuple[str, str, str, str, str], str] = {}
        self._snapshot_path = snapshot_path
        if self._snapshot_path is not None:
            self._load_snapshot()

    def claim_mapping(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
        channel_type: str,
        principal_role: str = "owner",
    ) -> IdentityChannelMappingRecord:
        """Claim mapping key and return existing/new pending mapping record."""

        key = _normalize_mapping_key(
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
        )
        mapping_id = self._mapping_id_by_key.get(key)
        if mapping_id is not None:
            existing = self._records_by_id.get(mapping_id)
            if existing is not None:
                return existing
        now = datetime.now(tz=UTC)
        created = IdentityChannelMappingRecord(
            mapping_id=str(uuid4()),
            connector=key[0],
            actor_external_id=key[1],
            guild_id=key[2],
            channel_id=key[3],
            channel_type=key[4],
            status="pending",
            created_at=now,
            updated_at=now,
            principal_role=principal_role,
        )
        self._records_by_id[created.mapping_id] = created
        self._mapping_id_by_key[key] = created.mapping_id
        self._flush_snapshot()
        return created

    def set_mapping_status(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
        channel_type: str,
        status: IdentityChannelStatus,
    ) -> IdentityChannelMappingRecord:
        """Set mapping status for one connector actor/channel mapping key."""

        key = _normalize_mapping_key(
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
        )
        mapping_id = self._mapping_id_by_key.get(key)
        if mapping_id is None:
            raise IdentityChannelRepositoryError(
                code="identity_channel_mapping_missing",
                message="identity channel mapping not found for status update",
            )
        existing = self._records_by_id.get(mapping_id)
        if existing is None:
            raise IdentityChannelRepositoryError(
                code="identity_channel_mapping_missing",
                message="identity channel mapping record not found",
            )
        updated = replace(existing, status=status, updated_at=datetime.now(tz=UTC))
        self._records_by_id[updated.mapping_id] = updated
        self._flush_snapshot()
        return updated

    def get_mapping(
        self,
        *,
        connector: str,
        actor_external_id: str,
        guild_id: str,
        channel_id: str,
        channel_type: str,
    ) -> IdentityChannelMappingRecord | None:
        """Load one mapping by normalized key."""

        key = _normalize_mapping_key(
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
        )
        mapping_id = self._mapping_id_by_key.get(key)
        if mapping_id is None:
            return None
        return self._records_by_id.get(mapping_id)

    def list_mappings(self) -> tuple[IdentityChannelMappingRecord, ...]:
        """List all persisted identity/channel mappings."""

        return tuple(self._records_by_id.values())

    def get_by_connector_actor(
        self,
        connector: str,
        actor_external_id: str,
    ) -> IdentityChannelMappingRecord | None:
        """Return the first verified mapping for (connector, actor_external_id), or None."""

        normalized_connector = connector.strip().lower()
        normalized_actor = actor_external_id.strip()
        for record in self._records_by_id.values():
            if (
                record.connector == normalized_connector
                and record.actor_external_id == normalized_actor
                and record.status == "verified"
            ):
                return record
        return None

    def _load_snapshot(self) -> None:
        path = self._resolved_snapshot_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise IdentityChannelRepositoryError(
                code="identity_channel_snapshot_load_failed",
                message=f"failed to load identity/channel snapshot: {path}",
            ) from error
        records = payload.get("mappings", [])
        if not isinstance(records, list):
            raise IdentityChannelRepositoryError(
                code="identity_channel_snapshot_invalid",
                message="identity/channel snapshot payload must include list mappings",
            )
        for raw in records:
            record = _mapping_from_dict(raw)
            self._records_by_id[record.mapping_id] = record
            key = _normalize_mapping_key(
                connector=record.connector,
                actor_external_id=record.actor_external_id,
                guild_id=record.guild_id,
                channel_id=record.channel_id,
                channel_type=record.channel_type,
            )
            self._mapping_id_by_key[key] = record.mapping_id

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        path = self._resolved_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mappings": [_mapping_to_dict(record) for record in self._records_by_id.values()],
        }
        try:
            path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        except OSError as error:
            raise IdentityChannelRepositoryError(
                code="identity_channel_snapshot_write_failed",
                message=f"failed to write identity/channel snapshot: {path}",
            ) from error

    def _resolved_snapshot_path(self) -> Path:
        if self._snapshot_path is not None:
            return self._snapshot_path
        return RuntimeSettings().identity_channel_snapshot_path


def _normalize_mapping_key(
    *,
    connector: str,
    actor_external_id: str,
    guild_id: str,
    channel_id: str,
    channel_type: str,
) -> tuple[str, str, str, str, str]:
    normalized = (
        connector.strip().lower(),
        actor_external_id.strip(),
        guild_id.strip(),
        channel_id.strip(),
        channel_type.strip().lower(),
    )
    if any(not value for value in normalized):
        raise IdentityChannelRepositoryError(
            code="identity_channel_mapping_invalid",
            message="connector identity/channel mapping key fields must be non-empty",
        )
    return normalized


def _mapping_to_dict(record: IdentityChannelMappingRecord) -> dict[str, object]:
    return {
        "mapping_id": record.mapping_id,
        "connector": record.connector,
        "actor_external_id": record.actor_external_id,
        "guild_id": record.guild_id,
        "channel_id": record.channel_id,
        "channel_type": record.channel_type,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "principal_role": record.principal_role,
    }


def _mapping_from_dict(raw: object) -> IdentityChannelMappingRecord:
    if not isinstance(raw, dict):
        raise IdentityChannelRepositoryError(
            code="identity_channel_snapshot_invalid_record",
            message="identity/channel snapshot record must be an object",
        )
    status = str(raw.get("status", "pending")).strip().lower()
    if status not in {"pending", "verified", "revoked"}:
        raise IdentityChannelRepositoryError(
            code="identity_channel_snapshot_invalid_status",
            message=f"invalid mapping status in snapshot: {status}",
        )
    return IdentityChannelMappingRecord(
        mapping_id=str(raw["mapping_id"]),
        connector=str(raw["connector"]),
        actor_external_id=str(raw["actor_external_id"]),
        guild_id=str(raw["guild_id"]),
        channel_id=str(raw["channel_id"]),
        channel_type=str(raw["channel_type"]),
        status=status,  # type: ignore[arg-type]
        created_at=datetime.fromisoformat(str(raw["created_at"])).astimezone(UTC),
        updated_at=datetime.fromisoformat(str(raw["updated_at"])).astimezone(UTC),
        principal_role=str(raw.get("principal_role", "owner")),
    )
