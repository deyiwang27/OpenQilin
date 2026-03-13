"""Tool service registry resolver."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.execution_sandbox.tools.read_tools import GovernedReadToolService
from openqilin.execution_sandbox.tools.write_tools import GovernedWriteToolService


@dataclass(frozen=True, slots=True)
class ToolServiceRegistry:
    """Resolved read/write tool services."""

    read_tools: GovernedReadToolService | None
    write_tools: GovernedWriteToolService | None
