"""Agent registry repository primitives for institutional-agent bootstrap."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from openqilin.shared_kernel.config import RuntimeSettings

_INSTITUTIONAL_ROLES = ("administrator", "auditor", "ceo", "cwo")


@dataclass(frozen=True, slots=True)
class AgentRecord:
    """Persisted agent record under governance registry control."""

    agent_id: str
    role: str
    agent_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class AgentRegistryRepositoryError(ValueError):
    """Raised when agent-registry snapshot persistence cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InMemoryAgentRegistryRepository:
    """In-memory agent registry with optional snapshot persistence."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:
        self._agents_by_id: dict[str, AgentRecord] = {}
        self._agent_id_by_role: dict[str, str] = {}
        self._snapshot_path = snapshot_path
        if self._snapshot_path is not None:
            self._load_snapshot()

    def bootstrap_institutional_agents(self) -> tuple[AgentRecord, ...]:
        """Ensure canonical institutional agents exist and return active records."""

        now = datetime.now(tz=UTC)
        for role in _INSTITUTIONAL_ROLES:
            existing = self.get_agent_by_role(role)
            if existing is None:
                record = AgentRecord(
                    agent_id=f"{role}_core",
                    role=role,
                    agent_type="institutional",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
                self._agents_by_id[record.agent_id] = record
                self._agent_id_by_role[record.role] = record.agent_id
                continue
            if existing.status != "active":
                self._agents_by_id[existing.agent_id] = replace(
                    existing,
                    status="active",
                    updated_at=now,
                )
        self._flush_snapshot()
        return tuple(
            sorted(
                (
                    record
                    for record in self._agents_by_id.values()
                    if record.agent_type == "institutional"
                ),
                key=lambda record: record.role,
            )
        )

    def get_agent_by_role(self, role: str) -> AgentRecord | None:
        """Load one agent by canonical role name."""

        agent_id = self._agent_id_by_role.get(role.strip().lower())
        if agent_id is None:
            return None
        return self._agents_by_id.get(agent_id)

    def list_agents(self, *, agent_type: str | None = None) -> tuple[AgentRecord, ...]:
        """List all persisted agents, optionally filtered by type."""

        records = tuple(self._agents_by_id.values())
        if agent_type is None:
            return records
        normalized = agent_type.strip().lower()
        return tuple(record for record in records if record.agent_type == normalized)

    def _load_snapshot(self) -> None:
        path = self._resolved_snapshot_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise AgentRegistryRepositoryError(
                code="agent_registry_snapshot_load_failed",
                message=f"failed to load agent-registry snapshot: {path}",
            ) from error
        records = payload.get("agents", [])
        if not isinstance(records, list):
            raise AgentRegistryRepositoryError(
                code="agent_registry_snapshot_invalid",
                message="agent-registry snapshot payload must include list agents",
            )
        for raw in records:
            record = _record_from_dict(raw)
            self._agents_by_id[record.agent_id] = record
            self._agent_id_by_role[record.role] = record.agent_id

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        path = self._resolved_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "agents": [_record_to_dict(record) for record in self._agents_by_id.values()],
        }
        try:
            path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        except OSError as error:
            raise AgentRegistryRepositoryError(
                code="agent_registry_snapshot_write_failed",
                message=f"failed to write agent-registry snapshot: {path}",
            ) from error

    def _resolved_snapshot_path(self) -> Path:
        if self._snapshot_path is not None:
            return self._snapshot_path
        return RuntimeSettings().agent_registry_snapshot_path


def _record_to_dict(record: AgentRecord) -> dict[str, object]:
    return {
        "agent_id": record.agent_id,
        "role": record.role,
        "agent_type": record.agent_type,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _record_from_dict(raw: object) -> AgentRecord:
    if not isinstance(raw, dict):
        raise AgentRegistryRepositoryError(
            code="agent_registry_snapshot_invalid_record",
            message="agent-registry snapshot record must be an object",
        )
    return AgentRecord(
        agent_id=str(raw["agent_id"]),
        role=str(raw["role"]),
        agent_type=str(raw["agent_type"]),
        status=str(raw["status"]),
        created_at=datetime.fromisoformat(str(raw["created_at"])).astimezone(UTC),
        updated_at=datetime.fromisoformat(str(raw["updated_at"])).astimezone(UTC),
    )
