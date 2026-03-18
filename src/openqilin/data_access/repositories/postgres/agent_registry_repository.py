"""PostgreSQL-backed agent registry repository replacing InMemoryAgentRegistryRepository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.repositories.agent_registry import (
    AgentRecord,
    AgentRegistryRepositoryError,
)

_INSTITUTIONAL_ROLES = ("administrator", "auditor", "ceo", "cwo", "cso", "secretary")

# Secretary is advisory-only: it must never be registered with a non-institutional type.
_ADVISORY_ONLY_ROLES: frozenset[str] = frozenset({"secretary"})


class PostgresAgentRegistryRepository:
    """PostgreSQL-backed agent registry with idempotent institutional bootstrap."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def bootstrap_institutional_agents(self) -> tuple[AgentRecord, ...]:
        """Ensure canonical institutional agents exist; return active records."""

        now = datetime.now(tz=UTC)
        for role in _INSTITUTIONAL_ROLES:
            existing = self.get_agent_by_role(role)
            if existing is not None and role in _ADVISORY_ONLY_ROLES:
                if existing.agent_type != "institutional":
                    raise AgentRegistryRepositoryError(
                        code="agent_registry_advisory_only_violation",
                        message=(
                            f"Role '{role}' must be registered with advisory-only capability "
                            f"(agent_type='institutional'). "
                            f"Found agent_type='{existing.agent_type}'. "
                            "Secretary cannot be granted command or mutation capabilities."
                        ),
                    )
            if existing is None:
                with self._session_factory() as session:
                    session.execute(
                        text(
                            """
                            INSERT INTO agents (agent_id, role, agent_type, status, created_at, updated_at)
                            VALUES (:agent_id, :role, :agent_type, :status, :created_at, :updated_at)
                            ON CONFLICT (role) DO NOTHING
                            """
                        ),
                        {
                            "agent_id": f"{role}_core",
                            "role": role,
                            "agent_type": "institutional",
                            "status": "active",
                            "created_at": now,
                            "updated_at": now,
                        },
                    )
                    session.commit()
            elif existing.status != "active":
                with self._session_factory() as session:
                    session.execute(
                        text(
                            """
                            UPDATE agents SET status = 'active', updated_at = :updated_at
                            WHERE role = :role
                            """
                        ),
                        {"role": role, "updated_at": now},
                    )
                    session.commit()
        return tuple(
            sorted(
                self.list_agents(agent_type="institutional"),
                key=lambda r: r.role,
            )
        )

    def get_agent_by_role(self, role: str) -> AgentRecord | None:
        """Load one agent by canonical role name."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text("SELECT * FROM agents WHERE role = :role"),
                    {"role": role.strip().lower()},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _agent_from_row(dict(row))

    def list_agents(self, *, agent_type: str | None = None) -> tuple[AgentRecord, ...]:
        """List all persisted agents, optionally filtered by type."""

        with self._session_factory() as session:
            if agent_type is None:
                rows = (
                    session.execute(text("SELECT * FROM agents ORDER BY role ASC")).mappings().all()
                )
            else:
                rows = (
                    session.execute(
                        text(
                            "SELECT * FROM agents WHERE agent_type = :agent_type ORDER BY role ASC"
                        ),
                        {"agent_type": agent_type.strip().lower()},
                    )
                    .mappings()
                    .all()
                )
        return tuple(_agent_from_row(dict(row)) for row in rows)


def _agent_from_row(row: dict[str, object]) -> AgentRecord:
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
    return AgentRecord(
        agent_id=str(row["agent_id"]),
        role=str(row["role"]),
        agent_type=str(row["agent_type"]),
        status=str(row["status"]),
        created_at=created_at,  # type: ignore[arg-type]
        updated_at=updated_at,  # type: ignore[arg-type]
    )
