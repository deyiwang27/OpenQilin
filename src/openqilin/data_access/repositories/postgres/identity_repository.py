"""PostgreSQL-backed identity/channel mapping repository replacing InMemoryIdentityChannelRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.repositories.identity_channels import (
    IdentityChannelMappingRecord,
    IdentityChannelRepositoryError,
    IdentityChannelStatus,
)


class PostgresIdentityMappingRepository:
    """PostgreSQL-backed connector identity/channel mapping repository."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
        """Claim mapping key; return existing or newly created pending mapping record."""

        key = _normalize_key(
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
        )
        existing = self.get_mapping(
            connector=key[0],
            actor_external_id=key[1],
            guild_id=key[2],
            channel_id=key[3],
            channel_type=key[4],
        )
        if existing is not None:
            return existing
        now = datetime.now(tz=UTC)
        record = IdentityChannelMappingRecord(
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
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO identity_channels (
                        mapping_id, connector, actor_external_id, guild_id,
                        channel_id, channel_type, status, created_at, updated_at, principal_role
                    ) VALUES (
                        :mapping_id, :connector, :actor_external_id, :guild_id,
                        :channel_id, :channel_type, :status, :created_at, :updated_at, :principal_role
                    )
                    ON CONFLICT (connector, actor_external_id, guild_id, channel_id, channel_type)
                    DO NOTHING
                    """
                ),
                {
                    "mapping_id": record.mapping_id,
                    "connector": record.connector,
                    "actor_external_id": record.actor_external_id,
                    "guild_id": record.guild_id,
                    "channel_id": record.channel_id,
                    "channel_type": record.channel_type,
                    "status": record.status,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                    "principal_role": record.principal_role,
                },
            )
            session.commit()
        # Re-fetch to handle ON CONFLICT race
        result = self.get_mapping(
            connector=key[0],
            actor_external_id=key[1],
            guild_id=key[2],
            channel_id=key[3],
            channel_type=key[4],
        )
        return result or record

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

        key = _normalize_key(
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
        )
        existing = self.get_mapping(
            connector=key[0],
            actor_external_id=key[1],
            guild_id=key[2],
            channel_id=key[3],
            channel_type=key[4],
        )
        if existing is None:
            raise IdentityChannelRepositoryError(
                code="identity_channel_mapping_missing",
                message="identity channel mapping not found for status update",
            )
        now = datetime.now(tz=UTC)
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    UPDATE identity_channels SET status = :status, updated_at = :updated_at
                    WHERE connector = :connector
                      AND actor_external_id = :actor_external_id
                      AND guild_id = :guild_id
                      AND channel_id = :channel_id
                      AND channel_type = :channel_type
                    """
                ),
                {
                    "status": status,
                    "updated_at": now,
                    "connector": key[0],
                    "actor_external_id": key[1],
                    "guild_id": key[2],
                    "channel_id": key[3],
                    "channel_type": key[4],
                },
            )
            session.commit()
        result = self.get_mapping(
            connector=key[0],
            actor_external_id=key[1],
            guild_id=key[2],
            channel_id=key[3],
            channel_type=key[4],
        )
        if result is None:
            raise IdentityChannelRepositoryError(
                code="identity_channel_mapping_missing",
                message="identity channel mapping record not found after update",
            )
        return result

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

        key = _normalize_key(
            connector=connector,
            actor_external_id=actor_external_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_type=channel_type,
        )
        with self._session_factory() as session:
            row = (
                session.execute(
                    text(
                        """
                    SELECT * FROM identity_channels
                    WHERE connector = :connector
                      AND actor_external_id = :actor_external_id
                      AND guild_id = :guild_id
                      AND channel_id = :channel_id
                      AND channel_type = :channel_type
                    """
                    ),
                    {
                        "connector": key[0],
                        "actor_external_id": key[1],
                        "guild_id": key[2],
                        "channel_id": key[3],
                        "channel_type": key[4],
                    },
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _mapping_from_row(dict(row))

    def list_mappings(self) -> tuple[IdentityChannelMappingRecord, ...]:
        """List all persisted identity/channel mappings."""

        with self._session_factory() as session:
            rows = (
                session.execute(text("SELECT * FROM identity_channels ORDER BY created_at ASC"))
                .mappings()
                .all()
            )
        return tuple(_mapping_from_row(dict(row)) for row in rows)

    def get_by_connector_actor(
        self,
        connector: str,
        actor_external_id: str,
    ) -> IdentityChannelMappingRecord | None:
        """Return the first verified mapping for (connector, actor_external_id), or None."""

        normalized_connector = connector.strip().lower()
        normalized_actor = actor_external_id.strip()
        with self._session_factory() as session:
            row = (
                session.execute(
                    text(
                        """
                    SELECT * FROM identity_channels
                    WHERE connector = :connector
                      AND actor_external_id = :actor_external_id
                      AND status = 'verified'
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                    ),
                    {
                        "connector": normalized_connector,
                        "actor_external_id": normalized_actor,
                    },
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _mapping_from_row(dict(row))


def _normalize_key(
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


def _mapping_from_row(row: dict[str, object]) -> IdentityChannelMappingRecord:
    created_at = row["created_at"]
    updated_at = row["updated_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at).astimezone(UTC)
    elif hasattr(created_at, "tzinfo") and created_at.tzinfo is None:  # type: ignore[attr-defined]
        created_at = created_at.replace(tzinfo=UTC)  # type: ignore[attr-defined]
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at).astimezone(UTC)
    elif hasattr(updated_at, "tzinfo") and updated_at.tzinfo is None:  # type: ignore[attr-defined]
        updated_at = updated_at.replace(tzinfo=UTC)  # type: ignore[attr-defined]
    status = str(row.get("status", "pending")).strip().lower()
    return IdentityChannelMappingRecord(
        mapping_id=str(row["mapping_id"]),
        connector=str(row["connector"]),
        actor_external_id=str(row["actor_external_id"]),
        guild_id=str(row["guild_id"]),
        channel_id=str(row["channel_id"]),
        channel_type=str(row["channel_type"]),
        status=status,  # type: ignore[arg-type]
        created_at=created_at,  # type: ignore[arg-type]
        updated_at=updated_at,  # type: ignore[arg-type]
        principal_role=str(row.get("principal_role", "owner")),
    )
