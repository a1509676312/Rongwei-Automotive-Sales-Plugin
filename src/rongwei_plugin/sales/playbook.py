"""Automotive-export sales decision framework for host AI models.

These are interpretation guides, not a hard-coded close-probability model.
The host model must cite case evidence and may return insufficient evidence.
"""

BUYING_STAGE_GUIDE = {
    "new_inquiry": "Initial contact; purchase requirements are not established.",
    "needs_discovery": "Buyer engages but decision-critical requirements remain unknown.",
    "qualified_interest": "A credible use case and meaningful requirements are emerging.",
    "active_evaluation": "Buyer compares vehicles, suppliers, configurations, or feasibility.",
    "commercial_alignment": "Buyer discusses concrete process, documents, payment, logistics, or terms.",
    "decision_pending": "A defined approval, internal decision, or buyer action remains outstanding.",
    "ready_for_order": "Buyer gives explicit credible signals to begin order confirmation or formal contracting.",
    "on_hold": "Buyer explicitly pauses or identifies a concrete external delay.",
    "lost_or_unresponsive": "Loss or sustained non-response is supported after proportionate follow-up.",
    "unknown": "Available evidence cannot support a reliable stage.",
}

INTENT_EVIDENCE_GUIDE = {
    "stronger_positive": [
        "Specific vehicle/model/configuration requirements",
        "Concrete quantity and destination country or port",
        "Defined purchase timeline or decision date",
        "Requests for export documents, inspection, VIN, or verifiable vehicle evidence",
        "Specific questions about payment process, shipping, import requirements, or contract steps",
        "Identifies decision participants or a procurement process",
        "Takes a concrete next step such as sharing requirements or requesting documents",
    ],
    "weak_or_ambiguous": [
        "Generic greeting or 'I am interested'",
        "An isolated price question without purchase context",
        "Likes, views, short acknowledgements, or vague promises",
        "Asking for a catalogue without identifying a use case",
    ],
    "negative_or_risk_signals": [
        "Repeatedly avoids decision-critical questions",
        "Contradicts previously stated requirements without explanation",
        "Requests unsupported guarantees or unrealistic commitments",
        "Stops responding after proportionate follow-up over a meaningful period",
    ],
    "interpretation_rule": (
        "Do not count signals mechanically. Explain context, recency, consistency, "
        "and evidence quality. A single strong signal can be outweighed by a material "
        "trust, payment, eligibility, or authority blocker."
    ),
}

OBJECTION_TAXONOMY = {
    "price_value": "Price, total landed cost, value comparison, or unclear cost components.",
    "trust_supplier": "Supplier identity, company legitimacy, proof, transaction history, or authenticity.",
    "vehicle_facts": "Model year, trim, condition, mileage, battery, left/right-hand drive, or specification uncertainty.",
    "logistics": "Shipping route, freight, port, schedule, insurance, or delivery responsibility.",
    "import_compliance": "Destination-country eligibility, customs, homologation, age limits, or documents.",
    "payment_safety": "Deposit, payment method, escrow, bank details, refund, or fraud concerns.",
    "timing": "Availability timing, procurement schedule, internal approval, or urgency mismatch.",
    "decision_authority": "Buyer is not the decision-maker or additional stakeholders are required.",
    "communication_gap": "Unanswered question, unclear explanation, language issue, or missing next step.",
}

SALESPERSON_REVIEW_DIMENSIONS = [
    "Did the seller answer the buyer's actual question directly?",
    "Did the seller ask only the most useful missing discovery question(s)?",
    "Did the seller connect verified vehicle value to the buyer's stated need?",
    "Did the seller support trust claims with evidence rather than superlatives?",
    "Did the seller handle the real objection instead of bypassing it?",
    "Did the seller guide the exchange toward a clear, proportionate next step?",
    "Did the seller avoid unsupported price, specification, stock, shipping, or delivery claims?",
    "Was follow-up timing appropriate to the buyer's behavior and stated timeline?",
]


def get_sales_playbook() -> dict:
    """Return the shared stage, intent, objection, and salesperson review guide."""
    return {
        "buying_stages": BUYING_STAGE_GUIDE.copy(),
        "intent_evidence": {
            key: list(value) if isinstance(value, list) else value
            for key, value in INTENT_EVIDENCE_GUIDE.items()
        },
        "objection_taxonomy": OBJECTION_TAXONOMY.copy(),
        "salesperson_review_dimensions": SALESPERSON_REVIEW_DIMENSIONS.copy(),
        "scoring_warning": (
            "No statistical close probability is supported. Any optional 0-100 value "
            "is a transparent evidence heuristic and must include rationale, coverage, "
            "and confidence."
        ),
    }
