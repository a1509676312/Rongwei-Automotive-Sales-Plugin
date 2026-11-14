"""Deterministic export quote calculations; no FX or freight data is invented."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TradeTerm = Literal["FOB", "CIF", "CIP"]


class QuoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_term: TradeTerm
    quantity: int = Field(ge=1, le=100000)
    currency: str = Field(min_length=3, max_length=8)
    vehicle_cost_per_unit: Decimal = Field(gt=0)
    inland_transport_total: Decimal = Field(ge=0, default=Decimal("0"))
    export_handling_total: Decimal = Field(ge=0, default=Decimal("0"))
    international_freight_total: Decimal = Field(ge=0, default=Decimal("0"))
    insurance_total: Decimal = Field(ge=0, default=Decimal("0"))
    other_included_costs: Decimal = Field(ge=0, default=Decimal("0"))
    profit_margin: Decimal = Field(ge=0, le=5, description="Markup on included cost, e.g. 0.08 = 8%.")
    origin_place: str | None = None
    named_destination: str | None = None
    freight_confirmed: bool = False
    insurance_confirmed: bool = False
    costs_confirmed: bool = False

    @model_validator(mode="after")
    def validate_term_requirements(self) -> "QuoteInput":
        if self.trade_term == "FOB" and not self.origin_place:
            raise ValueError("FOB requires a named port of shipment.")
        if self.trade_term in {"CIF", "CIP"} and not self.named_destination:
            raise ValueError("CIF requires a named destination port; CIP requires a named destination.")
        if self.trade_term in {"CIF", "CIP"} and not self.freight_confirmed:
            raise ValueError("International freight must be confirmed before issuing this quote.")
        if self.trade_term in {"CIF", "CIP"} and not self.insurance_confirmed:
            raise ValueError("Insurance must be confirmed before issuing this quote.")
        if self.trade_term in {"CIF", "CIP"} and self.insurance_total <= 0:
            raise ValueError("A confirmed, positive insurance cost is required.")
        return self


def calculate_quote(data: QuoteInput) -> dict:
    """Calculate a transparent estimate; user must verify all commercial inputs."""
    vehicle_total = data.vehicle_cost_per_unit * data.quantity
    included = vehicle_total + data.inland_transport_total + data.export_handling_total + data.other_included_costs
    if data.trade_term in {"CIF", "CIP"}:
        included += data.international_freight_total + data.insurance_total
    profit = included * data.profit_margin
    total = included + profit
    q = Decimal("0.01")
    money = lambda value: str(value.quantize(q, rounding=ROUND_HALF_UP))
    warnings = []
    if not data.costs_confirmed:
        warnings.append("车辆成本或其他成本尚未全部确认，结果只能作为内部测算。")
    if data.trade_term == "FOB":
        warnings.append("FOB 仅适用于海运或内河水运；确认约定装运港及装船交付安排。")
    if data.trade_term == "CIF":
        warnings.append("CIF 风险通常在装运港货物装上船时转移；卖方仍需安排至指定目的港的运费和保险。")
    if data.trade_term == "CIP":
        warnings.append("CIP 风险在货物交给第一承运人时转移；卖方承担至指定目的地的运输和约定保险。")
    if data.trade_term in {"CIF", "CIP"} and not data.freight_confirmed:
        warnings.append("国际运费未确认。")
    return {
        "trade_term": data.trade_term,
        "quantity": data.quantity,
        "currency": data.currency.upper(),
        "included_cost_total": money(included),
        "profit_amount": money(profit),
        "profit_markup_rate": str(data.profit_margin),
        "total_quote": money(total),
        "unit_quote": money(total / data.quantity),
        "origin_place": data.origin_place,
        "named_destination": data.named_destination,
        "commercial_inputs_confirmed": data.costs_confirmed and (
            data.trade_term == "FOB" or (data.freight_confirmed and data.insurance_confirmed)
        ),
        "warnings": warnings,
        "scope_note": "Calculation only. Confirm the contract, named place, cost scope and applicable Incoterms 2020 obligations before issuing a formal offer."
    }
