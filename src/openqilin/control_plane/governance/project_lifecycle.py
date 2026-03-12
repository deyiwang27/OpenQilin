"""Canonical project lifecycle transition guards for MVP governance flow."""

from __future__ import annotations

from typing import Literal, TypeAlias, cast

ProjectStatus: TypeAlias = Literal[
    "proposed",
    "approved",
    "active",
    "paused",
    "completed",
    "terminated",
    "archived",
]

_PROJECT_STATUS_VALUES: frozenset[str] = frozenset(
    {
        "proposed",
        "approved",
        "active",
        "paused",
        "completed",
        "terminated",
        "archived",
    }
)

_ALLOWED_TRANSITIONS: dict[ProjectStatus, frozenset[ProjectStatus]] = {
    "proposed": frozenset({"proposed", "approved"}),
    "approved": frozenset({"active"}),
    "active": frozenset({"paused", "completed", "terminated"}),
    "paused": frozenset({"active", "terminated"}),
    "completed": frozenset({"archived"}),
    "terminated": frozenset({"archived"}),
    "archived": frozenset(),
}

_TERMINAL_STATUSES: frozenset[ProjectStatus] = frozenset({"archived"})


class ProjectLifecycleError(ValueError):
    """Raised when project lifecycle status is invalid or transition is forbidden."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def parse_project_status(value: str) -> ProjectStatus:
    """Normalize and validate one project status value."""

    normalized = value.strip().lower()
    if normalized not in _PROJECT_STATUS_VALUES:
        raise ProjectLifecycleError(
            code="project_invalid_status",
            message=f"invalid project status: {value}",
        )
    return cast(ProjectStatus, normalized)


def allowed_project_status_transitions(current_status: str) -> tuple[ProjectStatus, ...]:
    """List canonical next statuses for current project status."""

    current = parse_project_status(current_status)
    return tuple(sorted(_ALLOWED_TRANSITIONS[current]))


def assert_project_transition(current_status: str, next_status: str) -> ProjectStatus:
    """Validate one status transition and return normalized next status."""

    current = parse_project_status(current_status)
    next_value = parse_project_status(next_status)
    if next_value in _ALLOWED_TRANSITIONS[current]:
        return next_value
    raise ProjectLifecycleError(
        code="project_invalid_transition",
        message=f"invalid project transition: {current} -> {next_value}",
    )


def is_terminal_project_status(status: str) -> bool:
    """Return whether project status is terminal in canonical lifecycle."""

    return parse_project_status(status) in _TERMINAL_STATUSES
