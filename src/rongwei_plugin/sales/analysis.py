"""Prepare a consistent sales-analysis brief and validate host-AI output.

This module does not pretend to be an LLM. It structures evidence and checks
policy invariants; the connected host model performs the actual reasoning.
"""
from __future__ import annotations

from typing import Any

from .playbook import get_sales_playbook

STAGES = {
    "new_inquiry", "needs_discovery", "qualified_interest", "active_evaluation",
    "commercial_alignment", "decision_pending", "ready_for_order",
    "on_hold", "lost_or_unresponsive", "unknown",
}
EVIDENCE_CLASSES = {
    "user_provided", "externally_verified", "inference", "unknown", "conflict",
}
INTENT_LEVELS = {"low", "developing", "qualified", "high", "insufficient_evidence"}
ANALYSIS_RULES = [
    "Reconstruct the conversation in chronological order and preserve speaker attribution.",
    "Separate explicit buyer statements from interpretations and unknowns.",
    "Keep every advertisement and vehicle candidate isolated; do not guess attribution.",
    "Assess intent from observable buying behavior; a price-only question is weak evidence by itself.",
    "Choose a buying stage and cite the evidence supporting it.",
    "Identify the most consequential objection or commercial risk, not a generic list.",
    "Review the salesperson's actual behavior and explain the commercial consequence of each weakness.",
    "Recommend one primary next objective and one concrete next action.",
    "Draft a concise, natural reply in the buyer's language only when a reply is appropriate.",
    "Never invent vehicle specifications, price, stock, shipping, customs, delivery, payment, or order facts.",
    "Do not offer or fabricate a price unless the user supplied an applicable verified price and authorized its use.",
    "A heuristic intent index is not a statistical close probability. Report evidence coverage and confidence separately.",
    "Replies are drafts only. Never send messages.",
]


def build_sales_analysis_context(context: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized, model-ready analysis brief without inventing facts."""
    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary")

    conversation = context.get("conversation") or []
    vehicles = context.get("vehicles") or []
    if not isinstance(conversation, list) or not isinstance(vehicles, list):
        raise ValueError("conversation and vehicles must be lists")

    normalized_messages = []
    for index, item in enumerate(conversation):
        if not isinstance(item, dict) or not str(item.get("text", "")).strip():
            continue
        speaker = item.get("speaker", "unknown")
        if speaker not in {"buyer", "seller", "other", "unknown"}:
            speaker = "unknown"
        normalized_messages.append({
            "sequence": index + 1,
            "speaker": speaker,
            "timestamp": item.get("timestamp"),
            "text": str(item["text"]).strip(),
            "evidence_id": item.get("evidence_id") or f"message-{index + 1}",
        })

    vehicle_candidates = []
    for item in vehicles:
        if not isinstance(item, dict):
            continue
        vehicle_candidates.append({
            "vehicle_id": item.get("vehicle_id", "unidentified"),
            "make": item.get("make"),
            "model": item.get("model"),
            "model_year": item.get("model_year"),
            "trim": item.get("trim"),
            "condition": item.get("condition"),
            "specification_notes": item.get("specification_notes"),
            "verification_status": item.get("verification_status", "unknown"),
            "source_reference": item.get("source_reference"),
        })

    return {
        "case_id": context.get("case_id"),
        "buyer_language": context.get("language"),
        "source": context.get("source") or {"source_confidence": "unknown"},
        "conversation": normalized_messages,
        "vehicle_candidates": vehicle_candidates,
        "buyer_requirements": context.get("buyer_requirements") or {},
        "prior_context": context.get("prior_context"),
        "analysis_rules": ANALYSIS_RULES.copy(),
        "sales_playbook": get_sales_playbook(),
        "required_decisions": [
            "buying_stage", "intent_assessment", "primary_next_objective",
            "recommended_next_action", "salesperson_review",
        ],
        "output_schema": "schemas/sales-analysis-result.schema.json",
    }


def validate_analysis_result(result: dict[str, Any]) -> dict[str, Any]:
    """Check critical policy invariants in a host model's structured result."""
    if not isinstance(result, dict):
        raise TypeError("analysis result must be a dictionary")

    errors: list[str] = []
    stage = result.get("buying_stage")
    if stage not in STAGES:
        errors.append(f"buying_stage must be one of: {', '.join(sorted(STAGES))}")

    intent = result.get("intent_assessment")
    if not isinstance(intent, dict):
        errors.append("intent_assessment must be an object")
    else:
        if intent.get("level") not in INTENT_LEVELS:
            errors.append("intent_assessment.level must be one of: " + ", ".join(sorted(INTENT_LEVELS)))
        score = intent.get("heuristic_index")
        if score is not None and (not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100):
            errors.append("heuristic_index must be an integer from 0 to 100 or null")
        if "close_probability" in intent or "probability_to_close" in intent:
            errors.append("Do not expose an uncalibrated close probability")
        if not intent.get("rationale"):
            errors.append("intent_assessment.rationale is required")
        if intent.get("evidence_coverage") not in {"low", "medium", "high"}:
            errors.append("intent_assessment.evidence_coverage must be low, medium, or high")
        if intent.get("confidence") not in {"low", "medium", "high"}:
            errors.append("intent_assessment.confidence must be low, medium, or high")

    for key in ("primary_next_objective", "recommended_next_action"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            errors.append(f"{key} is required and must be non-empty")

    evidence_items = result.get("evidence_and_confidence", []) or []
    if not isinstance(evidence_items, list):
        errors.append("evidence_and_confidence must be a list")
        evidence_items = []
    for item in evidence_items:
        if not isinstance(item, dict) or item.get("classification") not in EVIDENCE_CLASSES:
            errors.append("Each evidence item must use a valid classification")
            break

    # A draft must never be confused with an action taken by the plugin.
    if result.get("message_sent") is True or result.get("auto_send") is True:
        errors.append("Automatic message sending is prohibited")

    return {"valid": not errors, "errors": errors}
