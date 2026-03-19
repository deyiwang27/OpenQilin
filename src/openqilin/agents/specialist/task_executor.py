"""Specialist task execution boundary."""

from __future__ import annotations

from openqilin.agents.specialist.models import ToolNotAuthorizedError


class SpecialistTaskExecutor:
    """Validate tool access and execute within the approved sandbox boundary."""

    def execute(
        self,
        *,
        task_description: str,
        approved_tools: tuple[str, ...],
        tools_requested: tuple[str, ...],
    ) -> str:
        """Execute task with tool-access validation."""

        for tool in tools_requested:
            if tool not in approved_tools:
                raise ToolNotAuthorizedError(tool)
        return f"Task executed: {task_description[:200]}"
