"""PostgreSQL-backed budget ledger repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True, slots=True)
class BudgetAllocationRecord:
    id: str
    project_id: str
    currency_limit_usd: Decimal
    quota_limit_tokens: int
    window_type: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class BudgetReservationRecord:
    id: str
    task_id: str
    project_id: str
    reserved_usd: Decimal
    reserved_tokens: int
    status: str
    created_at: datetime
    settled_at: datetime | None


class PostgresBudgetLedgerRepository:
    """
    Raw-SQL repository for budget_allocations, budget_reservations, and budget_events.

    get_allocation() and get_spent_tokens() open their own sessions (read-only).
    insert_reservation() accepts a caller-owned session so it participates in the
    SELECT FOR UPDATE transaction held by PostgresBudgetRuntimeClient.
    settle_reservation(), release_reservation(), and insert_event() open their own sessions.
    """

    DEFAULT_CURRENCY_LIMIT_USD: Decimal = Decimal("10.00")
    DEFAULT_QUOTA_LIMIT_TOKENS: int = 500_000
    DEFAULT_WINDOW_TYPE: str = "per_project"
    DEFAULT_PROJECT_ID: str = "project-default"

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Public accessor for the session factory (used by PostgresBudgetRuntimeClient)."""
        return self._session_factory

    def get_allocation(self, project_id: str) -> BudgetAllocationRecord | None:
        """Return allocation row for project_id, or None if not found."""
        with self._session_factory() as session:
            row = session.execute(
                text(
                    "SELECT id, project_id, currency_limit_usd, quota_limit_tokens, "
                    "window_type, created_at, updated_at "
                    "FROM budget_allocations WHERE project_id = :project_id"
                ),
                {"project_id": project_id},
            ).fetchone()
            if row is None:
                return None
            return BudgetAllocationRecord(
                id=row.id,
                project_id=row.project_id,
                currency_limit_usd=Decimal(str(row.currency_limit_usd)),
                quota_limit_tokens=int(row.quota_limit_tokens),
                window_type=row.window_type,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def get_spent_tokens(self, project_id: str) -> int:
        """Sum reserved_tokens for all active reservations in this project."""
        with self._session_factory() as session:
            row = session.execute(
                text(
                    "SELECT COALESCE(SUM(reserved_tokens), 0) AS total "
                    "FROM budget_reservations "
                    "WHERE project_id = :project_id AND status = 'reserved'"
                ),
                {"project_id": project_id},
            ).fetchone()
            return int(row.total) if row else 0

    def find_active_reservation_id(self, task_id: str) -> str | None:
        """Return id of the active (status='reserved') reservation for task_id, or None."""
        with self._session_factory() as session:
            row = session.execute(
                text(
                    "SELECT id FROM budget_reservations "
                    "WHERE task_id = :task_id AND status = 'reserved'"
                ),
                {"task_id": task_id},
            ).fetchone()
            return str(row.id) if row is not None else None

    def insert_reservation(
        self,
        *,
        session: Session,
        task_id: str,
        project_id: str,
        reserved_usd: Decimal,
        reserved_tokens: int,
    ) -> BudgetReservationRecord:
        """
        Insert budget_reservations inside caller-managed transaction.

        Caller should hold allocation row lock from SELECT ... FOR UPDATE.
        """
        record = BudgetReservationRecord(
            id=str(uuid4()),
            task_id=task_id,
            project_id=project_id,
            reserved_usd=reserved_usd,
            reserved_tokens=reserved_tokens,
            status="reserved",
            created_at=datetime.now(tz=UTC),
            settled_at=None,
        )
        session.execute(
            text(
                "INSERT INTO budget_reservations "
                "(id, task_id, project_id, reserved_usd, reserved_tokens, status, created_at, settled_at) "
                "VALUES (:id, :task_id, :project_id, :reserved_usd, :reserved_tokens, "
                ":status, :created_at, :settled_at)"
            ),
            {
                "id": record.id,
                "task_id": record.task_id,
                "project_id": record.project_id,
                "reserved_usd": str(record.reserved_usd),
                "reserved_tokens": record.reserved_tokens,
                "status": record.status,
                "created_at": record.created_at,
                "settled_at": record.settled_at,
            },
        )
        return record

    def settle_reservation(self, *, reservation_id: str) -> None:
        """Mark a reservation settled. No-op if id missing or already settled."""
        with self._session_factory() as session:
            session.execute(
                text(
                    "UPDATE budget_reservations SET status = 'settled', settled_at = :now "
                    "WHERE id = :id AND status = 'reserved'"
                ),
                {"id": reservation_id, "now": datetime.now(tz=UTC)},
            )
            session.commit()

    def release_reservation(self, *, reservation_id: str) -> None:
        """Mark reservation released (task cancelled)."""
        with self._session_factory() as session:
            session.execute(
                text(
                    "UPDATE budget_reservations SET status = 'released', settled_at = :now "
                    "WHERE id = :id AND status = 'reserved'"
                ),
                {"id": reservation_id, "now": datetime.now(tz=UTC)},
            )
            session.commit()

    def insert_event(
        self,
        *,
        task_id: str,
        project_id: str,
        role: str,
        model_class: str,
        actual_tokens: int,
        actual_cost_usd: Decimal,
    ) -> None:
        """Append one budget_events row after LLM completion."""
        with self._session_factory() as session:
            session.execute(
                text(
                    "INSERT INTO budget_events "
                    "(id, task_id, project_id, role, model_class, actual_tokens, actual_cost_usd, created_at) "
                    "VALUES (:id, :task_id, :project_id, :role, :model_class, "
                    ":actual_tokens, :actual_cost_usd, :created_at)"
                ),
                {
                    "id": str(uuid4()),
                    "task_id": task_id,
                    "project_id": project_id,
                    "role": role,
                    "model_class": model_class,
                    "actual_tokens": actual_tokens,
                    "actual_cost_usd": str(actual_cost_usd),
                    "created_at": datetime.now(tz=UTC),
                },
            )
            session.commit()

    def seed_default_allocation(self) -> None:
        """
        Insert default project allocation if absent.

        Idempotent: safe to call on every startup.
        """
        if self.get_allocation(self.DEFAULT_PROJECT_ID) is not None:
            return

        now = datetime.now(tz=UTC)
        with self._session_factory() as session:
            session.execute(
                text(
                    "INSERT INTO budget_allocations "
                    "(id, project_id, currency_limit_usd, quota_limit_tokens, "
                    "window_type, created_at, updated_at) "
                    "VALUES (:id, :project_id, :currency_limit_usd, :quota_limit_tokens, "
                    ":window_type, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid4()),
                    "project_id": self.DEFAULT_PROJECT_ID,
                    "currency_limit_usd": str(self.DEFAULT_CURRENCY_LIMIT_USD),
                    "quota_limit_tokens": self.DEFAULT_QUOTA_LIMIT_TOKENS,
                    "window_type": self.DEFAULT_WINDOW_TYPE,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            session.commit()
