"""Budget runtime clients."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from openqilin.budget_runtime.models import BudgetReservationInput, BudgetReservationResult
from openqilin.data_access.repositories.postgres.budget_repository import (
    PostgresBudgetLedgerRepository,
)

_COST_UNIT_TO_USD = Decimal("0.0001")


class BudgetRuntimeClientError(RuntimeError):
    """Raised when budget runtime call cannot be completed."""


class PostgresBudgetRuntimeClient:
    """PostgreSQL-backed budget runtime client with atomic reservation semantics."""

    def __init__(
        self,
        *,
        ledger_repo: PostgresBudgetLedgerRepository,
        budget_version: str = "m15-budget-postgres-v1",
    ) -> None:
        self._ledger_repo = ledger_repo
        self._budget_version = budget_version

    def reserve(self, payload: BudgetReservationInput) -> BudgetReservationResult:
        """Reserve budget units for one task. Fail-closed to uncertain on DB errors."""

        project_scope = self._normalize_project_id(payload.project_id)
        try:
            decision = self._reserve_for_project(payload=payload, project_id=project_scope)
            if decision is not None:
                return decision
            if project_scope != self._ledger_repo.DEFAULT_PROJECT_ID:
                fallback_decision = self._reserve_for_project(
                    payload=payload,
                    project_id=self._ledger_repo.DEFAULT_PROJECT_ID,
                )
                if fallback_decision is not None:
                    return fallback_decision
            return BudgetReservationResult(
                decision="uncertain",
                reason_code="budget_allocation_missing",
                reason_message=f"missing budget allocation for project_id={project_scope!r}",
                reservation_id=None,
                remaining_units=None,
                budget_version=self._budget_version,
            )
        except Exception as error:
            return BudgetReservationResult(
                decision="uncertain",
                reason_code="budget_runtime_unavailable",
                reason_message=f"budget reservation unavailable: {error}",
                reservation_id=None,
                remaining_units=None,
                budget_version=self._budget_version,
            )

    def settle(self, task_id: str, reservation_id: str, actual_units: int) -> None:
        """Settle a reservation after task completion."""

        _ = task_id
        if not reservation_id.strip():
            return
        self._ledger_repo.settle_reservation(
            reservation_id=reservation_id,
            actual_units=max(actual_units, 0),
        )

    def release(self, task_id: str, reservation_id: str) -> None:
        """Release a reservation when task execution is cancelled."""

        _ = task_id
        if not reservation_id.strip():
            return
        self._ledger_repo.release_reservation(reservation_id=reservation_id)

    def _reserve_for_project(
        self,
        *,
        payload: BudgetReservationInput,
        project_id: str,
    ) -> BudgetReservationResult | None:
        estimate_tokens = max(payload.estimated_cost_units, 0)
        estimate_usd = Decimal(estimate_tokens) * _COST_UNIT_TO_USD

        with self._ledger_repo._session_factory() as session:
            allocation_row = session.execute(
                text(
                    "SELECT currency_limit_usd, quota_limit_tokens "
                    "FROM budget_allocations "
                    "WHERE project_id = :project_id "
                    "FOR UPDATE"
                ),
                {"project_id": project_id},
            ).fetchone()
            if allocation_row is None:
                return None

            spent_row = session.execute(
                text(
                    "SELECT COALESCE(SUM(reserved_tokens), 0) AS spent_tokens, "
                    "COALESCE(SUM(reserved_usd), 0) AS spent_usd "
                    "FROM budget_reservations "
                    "WHERE project_id = :project_id AND status = 'reserved'"
                ),
                {"project_id": project_id},
            ).fetchone()
            spent_tokens = int(spent_row.spent_tokens) if spent_row is not None else 0
            spent_usd = Decimal(str(spent_row.spent_usd)) if spent_row is not None else Decimal("0")

            quota_limit = int(allocation_row.quota_limit_tokens)
            currency_limit = Decimal(str(allocation_row.currency_limit_usd))

            if spent_tokens + estimate_tokens > quota_limit:
                return BudgetReservationResult(
                    decision="hard_breach",
                    reason_code="budget_quota_hard_breach",
                    reason_message="budget quota hard breach",
                    reservation_id=None,
                    remaining_units=max(quota_limit - spent_tokens, 0),
                    budget_version=self._budget_version,
                )
            if spent_usd + estimate_usd > currency_limit:
                return BudgetReservationResult(
                    decision="hard_breach",
                    reason_code="budget_currency_hard_breach",
                    reason_message="budget currency hard breach",
                    reservation_id=None,
                    remaining_units=max(quota_limit - spent_tokens, 0),
                    budget_version=self._budget_version,
                )

            record = self._ledger_repo.insert_reservation(
                session=session,
                task_id=payload.task_id,
                project_id=project_id,
                reserved_usd=estimate_usd,
                reserved_tokens=estimate_tokens,
            )
            session.commit()
            return BudgetReservationResult(
                decision="allow",
                reason_code="budget_reserved",
                reason_message="budget reserved",
                reservation_id=record.id,
                remaining_units=max(quota_limit - spent_tokens - estimate_tokens, 0),
                budget_version=self._budget_version,
            )

    def _normalize_project_id(self, project_id: str) -> str:
        normalized = project_id.strip()
        if normalized:
            return normalized
        return self._ledger_repo.DEFAULT_PROJECT_ID


class AlwaysAllowBudgetRuntimeClient:
    """Always-allow simulation budget client for local/unit tests."""

    def __init__(self, budget_version: str = "m1-budget-shell-v1") -> None:
        self._budget_version = budget_version
        self._remaining_units = 10_000

    def reserve(self, payload: BudgetReservationInput) -> BudgetReservationResult:
        """Evaluate and reserve budget for an admitted task."""

        if payload.command == "budget_error":
            raise BudgetRuntimeClientError("simulated budget runtime failure")

        if payload.command == "budget_uncertain":
            return BudgetReservationResult(
                decision="uncertain",
                reason_code="budget_uncertain",
                reason_message="budget runtime returned uncertainty",
                reservation_id=None,
                remaining_units=None,
                budget_version=self._budget_version,
            )

        if payload.command.startswith("budget_hard_breach"):
            return BudgetReservationResult(
                decision="hard_breach",
                reason_code="budget_quota_hard_breach",
                reason_message="budget hard breach",
                reservation_id=None,
                remaining_units=self._remaining_units,
                budget_version=self._budget_version,
            )

        if payload.command.startswith("budget_deny_"):
            return BudgetReservationResult(
                decision="deny",
                reason_code="budget_denied",
                reason_message="budget threshold denied request",
                reservation_id=None,
                remaining_units=self._remaining_units,
                budget_version=self._budget_version,
            )

        if payload.estimated_cost_units > self._remaining_units:
            return BudgetReservationResult(
                decision="deny",
                reason_code="budget_insufficient_capacity",
                reason_message="insufficient remaining budget units",
                reservation_id=None,
                remaining_units=self._remaining_units,
                budget_version=self._budget_version,
            )

        self._remaining_units -= payload.estimated_cost_units
        return BudgetReservationResult(
            decision="allow",
            reason_code="budget_reserved",
            reason_message="budget reserved",
            reservation_id=str(uuid4()),
            remaining_units=self._remaining_units,
            budget_version=self._budget_version,
        )

    def settle(self, task_id: str, reservation_id: str, actual_units: int) -> None:
        """No-op in simulation client."""

        _ = (task_id, reservation_id, actual_units)

    def release(self, task_id: str, reservation_id: str) -> None:
        """No-op in simulation client."""

        _ = (task_id, reservation_id)
