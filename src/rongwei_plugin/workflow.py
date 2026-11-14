"""Small deterministic helpers for the customer-to-order workflow."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal


def recommend_followup_delay(
    intent_band: Literal["S", "A", "B", "C", "D"],
    stage: str,
    *,
    customer_promised_at: datetime | None = None,
    our_commitment_at: datetime | None = None,
) -> datetime:
    """Honor explicit promises first; otherwise return a conservative local reminder time."""
    explicit = [value for value in (customer_promised_at, our_commitment_at) if value is not None]
    if explicit:
        return min(explicit)
    hours = {"S": 4, "A": 12, "B": 24, "C": 96, "D": 336}[intent_band]
    if stage in {"quote_sent", "commercial_process", "payment_pending"}:
        hours = min(hours, 12 if intent_band in {"S", "A"} else 24)
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def experience_relevance(
    *,
    record_country: str | None,
    requested_country: str | None,
    confidence: str,
) -> dict[str, str | bool]:
    """A historical case can guide a recommendation, never become a new customer's fact."""
    same_country = bool(record_country and requested_country and
                        record_country.casefold() == requested_country.casefold())
    labels = {
        "verified": "已验证经验",
        "repeated_pattern": "多次出现的业务规律",
        "single_case": "单次历史经验",
        "inference": "AI 推测",
    }
    return {
        "may_recommend": same_country and confidence in labels,
        "must_confirm_with_new_customer": True,
        "evidence_level": labels.get(confidence, "未知经验等级"),
        "reason": "同国家历史记录仅作为候选参考，不能代替新客户确认。" if same_country
                  else "国家不匹配或未知，不应将该经验用于目的地推荐。",
    }
