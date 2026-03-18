"""PostgreSQL-backed repository for project space bindings."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.project_spaces.models import BindingState, ProjectSpaceBinding


class PostgresProjectSpaceBindingRepository:
    """Durable store for project_space_bindings rows."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def insert(self, binding: ProjectSpaceBinding) -> ProjectSpaceBinding:
        """Persist a new binding record; returns the stored binding."""

        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO project_space_bindings
                        (id, project_id, guild_id, channel_id,
                         binding_state, default_recipient, created_at, updated_at)
                    VALUES
                        (:id, :project_id, :guild_id, :channel_id,
                         :binding_state, :default_recipient, :created_at, :updated_at)
                    """
                ),
                {
                    "id": binding.id,
                    "project_id": binding.project_id,
                    "guild_id": binding.guild_id,
                    "channel_id": binding.channel_id,
                    "binding_state": binding.binding_state.value,
                    "default_recipient": binding.default_recipient,
                    "created_at": binding.created_at,
                    "updated_at": binding.updated_at,
                },
            )
            session.commit()
        return binding

    def find_by_channel(self, guild_id: str, channel_id: str) -> ProjectSpaceBinding | None:
        """Look up a binding by (guild_id, channel_id); returns None if not found."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT * FROM project_space_bindings
                        WHERE guild_id = :guild_id AND channel_id = :channel_id
                        """
                    ),
                    {"guild_id": guild_id, "channel_id": channel_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _binding_from_row(dict(row))

    def find_by_project_id(self, project_id: str) -> ProjectSpaceBinding | None:
        """Look up the binding for a given project_id; returns None if not found."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text("SELECT * FROM project_space_bindings WHERE project_id = :project_id"),
                    {"project_id": project_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _binding_from_row(dict(row))

    def update_state(self, binding_id: str, state: BindingState) -> ProjectSpaceBinding:
        """Transition binding_state; returns the updated record."""

        now = datetime.now(tz=UTC)
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    UPDATE project_space_bindings
                    SET binding_state = :state, updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {"state": state.value, "updated_at": now, "id": binding_id},
            )
            session.commit()
            row = (
                session.execute(
                    text("SELECT * FROM project_space_bindings WHERE id = :id"),
                    {"id": binding_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ValueError(f"Binding not found after update: {binding_id}")
        return _binding_from_row(dict(row))


def build_project_space_binding(
    project_id: str,
    guild_id: str,
    channel_id: str,
    *,
    default_recipient: str = "project_manager",
    state: BindingState = BindingState.PROPOSED,
) -> ProjectSpaceBinding:
    """Factory for new ProjectSpaceBinding records."""

    now = datetime.now(tz=UTC)
    return ProjectSpaceBinding(
        id=str(uuid4()),
        project_id=project_id,
        guild_id=guild_id,
        channel_id=channel_id,
        binding_state=state,
        default_recipient=default_recipient,
        created_at=now,
        updated_at=now,
    )


def _binding_from_row(row: dict[str, object]) -> ProjectSpaceBinding:
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
    return ProjectSpaceBinding(
        id=str(row["id"]),
        project_id=str(row["project_id"]),
        guild_id=str(row["guild_id"]),
        channel_id=str(row["channel_id"]),
        binding_state=BindingState(str(row["binding_state"])),
        default_recipient=str(row["default_recipient"]),
        created_at=created_at,  # type: ignore[arg-type]
        updated_at=updated_at,  # type: ignore[arg-type]
    )
