"""Transaction execution helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.db.session import session_scope

ResultT = TypeVar("ResultT")


def run_in_transaction(
    *,
    session_factory: sessionmaker[Session],
    operation: Callable[[Session], ResultT],
) -> ResultT:
    """Execute callback within managed database transaction scope."""

    with session_scope(session_factory) as session:
        return operation(session)
