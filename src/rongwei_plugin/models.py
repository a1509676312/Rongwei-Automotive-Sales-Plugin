"""Canonical, provider-neutral data contracts.

The host AI extracts facts and evidence from customer material. The plugin validates
those observations and calculates transparent, deterministic sales indicators.
Do not persist raw customer conversations or direct personal contact data by default.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EvidenceSource = Literal[
    "customer_message", "customer_image", "user_note", "advertisement", "verified_external_source"
]

SignalKey = Literal[
    "vehicle_requirements_specific", "quantity_confirmed", "destination_confirmed",
    "buyer_role_confirmed", "purchase_timeline_30d", "purchase_timeline_90d",
    "asks_technical_detail", "asks_logistics_detail", "asks_compliance_documents",
    "asks_payment_process", "requests_proforma", "requests_contract",
    "agrees_concrete_next_step", "shares_business_identity", "shares_import_documents",
    "repeated_specific_engagement", "explicitly_browsing_only",
    "declines_core_qualification", "repeated_unanswered_followups",
    "contradictory_requirements",
]

MilestoneKey = Literal[
    "vehicle_requirements_confirmed", "solution_agreed", "commercial_terms_discussed",
    "shipping_process_discussed", "proforma_requested", "contract_requested",
    "payment_initiated", "payment_received", "order_confirmed", "explicitly_declined",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceRecord(ContractModel):
    """A concise traceable evidence item, not a dump of a private conversation."""
    id: str = Field(min_length=1, max_length=80)
    source: EvidenceSource
    summary: str = Field(min_length=1, max_length=500)
    observed_at: datetime | None = None
    source_ref: str | None = Field(default=None, max_length=160)


class ObservedSignal(ContractModel):
    key: SignalKey
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


class ObservedMilestone(ContractModel):
    key: MilestoneKey
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


class LeadFacts(ContractModel):
    """Only facts the host AI can ground in supplied material."""
    vehicle_brand: str | None = Field(default=None, max_length=100)
    vehicle_model: str | None = Field(default=None, max_length=160)
    model_year: str | None = Field(default=None, max_length=40)
    configuration: str | None = Field(default=None, max_length=300)
    destination_country: str | None = Field(default=None, max_length=100)
    destination_port: str | None = Field(default=None, max_length=120)
    quantity: int | None = Field(default=None, ge=1, le=100000)
    buyer_type: Literal["dealer", "importer", "fleet", "end_user", "broker", "unknown"] = "unknown"
    use_case: str | None = Field(default=None, max_length=300)
    purchase_timeline_days: int | None = Field(default=None, ge=0, le=3650)
    decision_maker_known: bool | None = None
    buyer_language: str | None = Field(default=None, max_length=60)


class LeadInput(ContractModel):
    """Input to an evidence-based lead assessment.

    case_ref must be an opaque identifier. Never put a phone number, email, name,
    WhatsApp ID, or other direct identifier in this field.
    """
    case_ref: str | None = Field(default=None, max_length=100)
    advertisement_ref: str | None = Field(default=None, max_length=100)
    facts: LeadFacts = Field(default_factory=LeadFacts)
    evidence: list[EvidenceRecord] = Field(default_factory=list, max_length=100)
    signals: list[ObservedSignal] = Field(default_factory=list, max_length=100)
    milestones: list[ObservedMilestone] = Field(default_factory=list, max_length=50)
    blockers: list[str] = Field(default_factory=list, max_length=30)
    prior_context_summary: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_evidence_references(self) -> "LeadInput":
        evidence_ids = [item.id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence record IDs must be unique.")
        known = set(evidence_ids)
        for item in [*self.signals, *self.milestones]:
            missing = sorted(set(item.evidence_ids) - known)
            if missing:
                raise ValueError(f"Unknown evidence IDs referenced: {', '.join(missing)}")
        return self


class ScoreBand(ContractModel):
    label: Literal[
        "insufficient_evidence", "early_inquiry", "qualified_potential",
        "strong_buying_process", "order_process"
    ]
    description: str


class SignalScore(ContractModel):
    key: SignalKey
    points: int
    evidence_ids: list[str]


class LeadAssessment(ContractModel):
    case_ref: str | None
    advertisement_ref: str | None
    evidence_score: int = Field(ge=0, le=100)
    score_is_close_probability: Literal[False] = False
    band: ScoreBand
    confidence: Literal["low", "medium", "high"]
    evidence_coverage: int = Field(ge=0, le=100)
    current_stage: Literal[
        "new_inquiry", "needs_discovery", "qualified_opportunity", "solution_alignment",
        "commercial_process", "order_process", "payment_pending", "order_confirmed", "closed_lost"
    ]
    stage_reason: str
    positive_signals: list[SignalScore]
    caution_signals: list[str]
    blockers: list[str]
    missing_information: list[str]
    next_objective: str
    next_action: str
    reply_strategy: str
    follow_up_trigger: str
    verification_before_commitment: list[str]
