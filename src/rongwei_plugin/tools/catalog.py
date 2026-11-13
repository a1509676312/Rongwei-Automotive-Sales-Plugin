"""Canonical tool catalog and dispatch.

Provider adapters should translate this catalog; they must not reimplement domain rules.
"""
from __future__ import annotations

from typing import Any

from rongwei_plugin.models import (
    LeadInput,
    ObjectionRequest,
    SalesExecutionInput,
)
from rongwei_plugin.sales.playbook import get_objection_plan
from rongwei_plugin.sales.review import review_sales_execution
from rongwei_plugin.sales.scoring import assess_lead

_TOOL_SCHEMAS: dict[str, tuple[str, str, type]] = {
    "rw_assess_automotive_export_lead": (
        "Assess a car-export lead from structured facts and traceable evidence. "
        "Returns an explainable evidence index, confidence, stage, missing information, "
        "and next action. This is not a close probability and does not send messages.",
        "assess",
        LeadInput,
    ),
    "rw_get_objection_playbook": (
        "Get a practical, evidence-safe sales strategy for one automotive-export objection. "
        "Returns what to verify, the objective, one discovery question, and claims to avoid.",
        "objection",
        ObjectionRequest,
    ),
    "rw_review_sales_execution": (
        "Review a salesperson's actions in a customer conversation. Identifies missed answers, "
        "weak follow-up, missing next steps, and unsupported claims from structured observations.",
        "review",
        SalesExecutionInput,
    ),
}


def get_tool_catalog() -> list[dict[str, Any]]:
    """Return provider-neutral function definitions in OpenAI-style tool format."""
    models = {
        "assess": LeadInput,
        "objection": ObjectionRequest,
        "review": SalesExecutionInput,
    }
    result = []
    for name, (description, model_key, _) in _TOOL_SCHEMAS.items():
        result.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": models[model_key].model_json_schema(),
            },
        })
    return result


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate arguments and execute a registered tool."""
    if name not in _TOOL_SCHEMAS:
        raise ValueError(f"Unknown Rongwei tool: {name}")

    _, operation, model = _TOOL_SCHEMAS[name]
    payload = model.model_validate(arguments)

    if operation == "assess":
        result = assess_lead(payload)
    elif operation == "objection":
        result = get_objection_plan(payload)
    else:
        result = review_sales_execution(payload)

    return result.model_dump(mode="json")


def registered_tool_names() -> tuple[str, ...]:
    return tuple(_TOOL_SCHEMAS)
