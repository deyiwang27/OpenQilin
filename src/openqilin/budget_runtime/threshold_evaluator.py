"""Budget threshold estimation for reservation checks."""

from __future__ import annotations


def estimate_cost_units(command: str, args: tuple[str, ...]) -> int:
    """Estimate cost units for a command execution request."""

    base_units = 10
    arg_units = len(args) * 2
    command_units = min(len(command), 24)
    return base_units + arg_units + command_units
