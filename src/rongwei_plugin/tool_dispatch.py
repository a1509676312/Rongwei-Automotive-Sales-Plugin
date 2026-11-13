"""Execute model-originated tool calls using Rongwei's canonical dispatcher.

This module does not call any LLM provider. The host application sends provider tool
calls here (or to the REST endpoint), receives tool results, and returns those results
to the same provider according to its conversation protocol.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

from rongwei_plugin.tools.catalog import execute_tool, registered_tool_names


class ToolCallDispatchError(ValueError):
    """Raised when a provider call batch is malformed or exceeds safety limits."""


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, BaseModel):
        dumped = value.model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    raise ToolCallDispatchError("Tool call must be a mapping or a Pydantic model.")


def execute_provider_tool_calls(
    tool_calls: Iterable[Any],
    *,
    max_calls: int = 8,
) -> list[dict[str, str]]:
    """Execute a bounded batch and return provider-style role=tool messages.

    Unknown tools and invalid arguments return safe error messages tied to the original
    call ID. Argument values are never echoed into errors or logs. The caller must append
    the original assistant tool-call message unchanged before appending these results.
    """
    calls = list(tool_calls)
    if not 1 <= max_calls <= 32:
        raise ValueError("max_calls must be between 1 and 32.")
    if len(calls) > max_calls:
        raise ToolCallDispatchError(f"Tool-call batch exceeds the configured limit ({max_calls}).")

    normalized: list[tuple[str, str, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    for raw in calls:
        item = _as_mapping(raw)
        call_id = item.get("id")
        function = item.get("function")
        if not isinstance(call_id, str) or not call_id.strip():
            raise ToolCallDispatchError("Each tool call must include a non-empty provider call ID.")
        if call_id in seen_ids:
            raise ToolCallDispatchError("Duplicate provider tool-call IDs are not allowed.")
        seen_ids.add(call_id)

        if isinstance(function, BaseModel):
            function = function.model_dump(exclude_none=True)
        if not isinstance(function, dict):
            raise ToolCallDispatchError("Each tool call must include a function object.")
        name = function.get("name")
        raw_arguments = function.get("arguments", "{}")
        if not isinstance(name, str) or not name:
            raise ToolCallDispatchError("Each tool call must include a function name.")

        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = None
        else:
            arguments = raw_arguments

        normalized.append((call_id, name, arguments if isinstance(arguments, dict) else {}))

    results: list[dict[str, str]] = []
    known_tools = set(registered_tool_names())
    for call_id, name, arguments in normalized:
        if name not in known_tools:
            payload = {"ok": False, "error": "unknown_tool"}
        else:
            try:
                output = execute_tool(name, arguments)
                payload = {"ok": True, "result": output}
            except Exception as exc:  # noqa: BLE001 - convert provider tool failures to safe tool messages.
                # Do not echo the supplied argument values or arbitrary exception text.
                payload = {
                    "ok": False,
                    "error": "invalid_tool_arguments",
                    "detail": type(exc).__name__,
                }
        results.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        })
    return results
