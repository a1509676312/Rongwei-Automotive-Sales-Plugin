"""DeepSeek Chat Completions adapter for Rongwei sales analysis.

Install the optional dependency with: pip install -e ".[deepseek]"
Set DEEPSEEK_API_KEY in the local environment. Never commit credentials.
"""
from __future__ import annotations

import json
import os
from typing import Any

from rongwei_plugin.sales.analysis import (
    build_sales_analysis_context,
    validate_analysis_result,
)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "prepare_sales_analysis",
            "description": (
                "Prepare and normalize automotive-export buyer/seller conversation, "
                "advertisement, vehicle candidates, and buyer requirements before analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {
                        "type": "object",
                        "description": "Canonical automotive export sales case context supplied by the user."
                    }
                },
                "required": ["context"],
                "additionalProperties": False,
            },
        },
    }
]

SYSTEM_PROMPT = """You are an experienced automotive-export sales director.
Analyze the buyer's real purchase intent and the seller's performance using only the supplied evidence.
First call prepare_sales_analysis with the complete case context. Then analyze the returned normalized context and playbook.
Do not confuse a price-only inquiry with a qualified buyer. Explain buying-stage decisions with evidence.
Identify the buyer's strongest concern, the seller's concrete mistakes (if any), and one primary next objective.
Keep different advertisements and vehicle candidates separate.
Never invent vehicle specifications, model year, condition, stock, price, shipping, customs eligibility, delivery, payment, or order facts.
Do not offer a price unless the user supplied an applicable verified price and explicitly authorized its use.
Never present an uncalibrated heuristic score as close probability. Report intent level, evidence coverage, and confidence separately.
Draft a natural, concise reply in the buyer's language only when appropriate. Replies are drafts only; never send.
Return one JSON object with these keys:
conversation_summary, vehicle_and_ad_attribution, buyer_requirements, buying_stage,
intent_assessment (level, heuristic_index or null, rationale, evidence_coverage, confidence),
positive_signals, objections_and_risks, missing_critical_information, salesperson_review,
primary_next_objective, recommended_next_action, reply_draft, reply_chinese_explanation,
follow_up_trigger, fact_checks_required, evidence_and_confidence.
For evidence_and_confidence, classify each claim as user_provided, externally_verified, inference, unknown, or conflict.
If evidence is insufficient, use unknown/insufficient_evidence rather than guessing.
"""

def dispatch_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch only tools implemented by this plugin; reject unknown names."""
    if name != "prepare_sales_analysis":
        raise ValueError(f"Unsupported Rongwei tool: {name}")
    context = arguments.get("context")
    if not isinstance(context, dict):
        raise ValueError("prepare_sales_analysis requires an object named 'context'")
    return build_sales_analysis_context(context)


def analyze_case(
    context: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str | None = None,
    max_tool_rounds: int = 3,
) -> dict[str, Any]:
    """Run a complete DeepSeek analysis with plugin tool calls and JSON output.

    This function requires a real DeepSeek API key and network access at runtime.
    """
    key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY. Set it in your local environment.")
    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('Install the DeepSeek extra: pip install -e ".[deepseek]"') from exc

    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
    selected_model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({"context": context}, ensure_ascii=False)},
    ]

    usage: dict[str, Any] | None = None
    for round_index in range(max_tool_rounds + 1):
        kwargs: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if round_index < max_tool_rounds:
            kwargs["tools"] = TOOL_DEFINITIONS
            kwargs["tool_choice"] = "required" if round_index == 0 else "auto"
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        usage = response.usage.model_dump() if response.usage else None
        message = choice.message
        tool_calls = getattr(message, "tool_calls", None) or []

        if tool_calls:
            messages.append(message.model_dump(exclude_none=True))
            for tool_call in tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                    result = dispatch_tool_call(tool_call.function.name, arguments)
                    tool_content = {"ok": True, "result": result}
                except Exception as exc:
                    tool_content = {"ok": False, "error": str(exc)}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_content, ensure_ascii=False),
                })
            continue

        if choice.finish_reason == "length":
            raise RuntimeError("DeepSeek response was truncated (finish_reason=length). Increase output capacity or shorten the input.")
        if not message.content:
            raise RuntimeError(f"DeepSeek returned no analysis content (finish_reason={choice.finish_reason}).")
        try:
            analysis = json.loads(message.content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("DeepSeek returned content that is not valid JSON.") from exc

        validation = validate_analysis_result(analysis)
        return {
            "provider": "deepseek",
            "model": selected_model,
            "analysis": analysis,
            "validation": validation,
            "usage": usage,
        }

    raise RuntimeError("DeepSeek did not complete analysis within the configured tool-call rounds.")
