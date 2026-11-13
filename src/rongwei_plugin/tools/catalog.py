"""Canonical tool catalog and dispatch.

Provider adapters should translate this catalog; they must not reimplement domain rules.
"""
from __future__ import annotations

from typing import Any

from rongwei_plugin.models import LeadInput
from rongwei_plugin.sales.scoring import assess_lead

_TOOL_NAME = "rw_assess_automotive_export_lead"


def get_tool_catalog() -> list[dict[str, Any]]:
    """Return provider-neutral function definitions in OpenAI-style tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": _TOOL_NAME,
                "description": (
                    "Evaluate an automotive-export sales opportunity from structured facts "
                    "and evidence. Returns an explainable evidence index, confidence, stage, "
                    "missing buyer information, blockers, and the next sales action. "
                    "The score is not a close probability. Do not use for sending messages."
                ),
                "parameters": LeadInput.model_json_schema(),
            },
        }
    ]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate arguments and execute a registered tool."""
    if name != _TOOL_NAME:
        raise ValueError(f"Unknown Rongwei tool: {name}")
    payload = LeadInput.model_validate(arguments)
    return assess_lead(payload).model_dump(mode="json")


def registered_tool_names() -> tuple[str, ...]:
    return (_TOOL_NAME,)
