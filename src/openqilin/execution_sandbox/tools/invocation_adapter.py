"""Tool command parsing and invocation adapter."""

from __future__ import annotations

import json
from typing import Mapping

from openqilin.execution_sandbox.tools.contracts import ToolCallContext, ToolResult
from openqilin.execution_sandbox.tools.registry_resolver import ToolServiceRegistry


def parse_tool_command_args(args: tuple[str, ...]) -> tuple[str, Mapping[str, object]] | None:
    """Parse canonical tool command args from owner command payload."""

    if len(args) == 0:
        return None
    raw_first = args[0].strip()
    if raw_first.startswith("{"):
        try:
            payload = json.loads(raw_first)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        tool_name = str(payload.get("tool") or "").strip().lower()
        raw_arguments = payload.get("arguments") or {}
        if not tool_name:
            return None
        if not isinstance(raw_arguments, dict):
            return None
        return tool_name, raw_arguments

    tool_name = raw_first.lower()
    if len(args) == 1:
        return tool_name, {}
    raw_second = args[1].strip()
    if not raw_second:
        return tool_name, {}
    if raw_second.startswith("{"):
        try:
            payload = json.loads(raw_second)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return tool_name, payload
    return tool_name, {"value": raw_second}


def invoke_tool_command(
    *,
    command: str,
    args: tuple[str, ...],
    context: ToolCallContext,
    registry: ToolServiceRegistry,
) -> ToolResult | None:
    """Invoke explicit tool command (`tool_read` or `tool_write`)."""

    parsed = parse_tool_command_args(args)
    if parsed is None:
        return None
    tool_name, arguments = parsed
    if command == "tool_read":
        if registry.read_tools is None:
            return None
        return registry.read_tools.call_tool(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
        )
    if command == "tool_write":
        if registry.write_tools is None:
            return None
        return registry.write_tools.call_tool(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
        )
    return None
