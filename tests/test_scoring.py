from pydantic import ValidationError
import pytest

from rongwei_plugin.models import LeadInput
from rongwei_plugin.sales.scoring import assess_lead


def test_price_only_question_is_not_a_high_intent_signal():
    data = LeadInput(
        evidence=[{"id": "e1", "source": "customer_message", "summary": "客户只问有没有最低价。"}],
    )
    result = assess_lead(data)
    assert result.evidence_score == 0
    assert result.band.label == "insufficient_evidence"
    assert result.confidence == "low"
    assert result.current_stage == "needs_discovery"


def test_qualified_buyer_gets_traceable_evidence_score():
    data = LeadInput(
        facts={
            "vehicle_model": "Model X",
            "quantity": 5,
            "destination_country": "Kenya",
            "buyer_type": "dealer",
            "purchase_timeline_days": 30,
            "decision_maker_known": True,
        },
        evidence=[
            {"id": "e1", "source": "customer_message", "summary": "明确车型"},
            {"id": "e2", "source": "customer_message", "summary": "明确采购数量"},
            {"id": "e3", "source": "customer_message", "summary": "明确目的国家"},
            {"id": "e4", "source": "customer_message", "summary": "客户说明自己是经销商"},
            {"id": "e5", "source": "customer_message", "summary": "说明一个月内采购"},
        ],
        fact_evidence={
            "vehicle_model": ["e1"],
            "quantity": ["e2"],
            "destination_country": ["e3"],
            "buyer_type": ["e4"],
            "purchase_timeline_days": ["e5"],
            "decision_maker_known": ["e4"],
        },
        signals=[
            {"key": "vehicle_requirements_specific", "evidence_ids": ["e1"]},
            {"key": "quantity_confirmed", "evidence_ids": ["e2"]},
            {"key": "destination_confirmed", "evidence_ids": ["e3"]},
            {"key": "purchase_timeline_30d", "evidence_ids": ["e5"]},
        ],
    )
    result = assess_lead(data)
    assert result.evidence_score == 36
    assert result.band.label == "qualified_potential"
    assert result.confidence == "high"
    assert result.evidence_coverage == 100
    assert result.current_stage == "qualified_opportunity"
    assert all(item.evidence_ids for item in result.positive_signals)


def test_repeated_signal_is_not_double_counted():
    data = LeadInput(
        evidence=[{"id": "e1", "source": "customer_message", "summary": "客户确认数量"}],
        signals=[
            {"key": "quantity_confirmed", "evidence_ids": ["e1"]},
            {"key": "quantity_confirmed", "evidence_ids": ["e1"]},
        ],
    )
    assert assess_lead(data).evidence_score == 10


def test_order_stage_requires_explicit_milestone():
    data = LeadInput(
        evidence=[{"id": "e1", "source": "customer_message", "summary": "客户询问技术配置"}],
        signals=[{"key": "asks_technical_detail", "evidence_ids": ["e1"]}],
    )
    result = assess_lead(data)
    assert result.current_stage != "order_process"
    assert result.band.label != "order_process"


def test_unknown_evidence_reference_is_rejected():
    with pytest.raises(ValidationError):
        LeadInput(signals=[{"key": "quantity_confirmed", "evidence_ids": ["missing"]}])


def test_payment_intent_is_not_payment_received():
    data = LeadInput(
        evidence=[{"id": "e1", "source": "customer_message", "summary": "客户说准备安排付款"}],
        milestones=[{"key": "payment_initiated", "evidence_ids": ["e1"]}],
    )
    result = assess_lead(data)
    assert result.current_stage == "payment_pending"
    assert "未收到可核验凭证前，不得把付款意向写成已付款。" in result.verification_before_commitment


def test_payment_received_requires_user_or_external_verification():
    with pytest.raises(ValidationError):
        LeadInput(
            evidence=[{"id": "e1", "source": "customer_message", "summary": "客户说已付款"}],
            milestones=[{"key": "payment_received", "evidence_ids": ["e1"]}],
        )

    data = LeadInput(
        evidence=[{"id": "e1", "source": "user_note", "summary": "卖方已核对银行到账记录", "is_verified": True}],
        milestones=[{"key": "payment_received", "evidence_ids": ["e1"]}],
    )
    assert assess_lead(data).current_stage == "payment_received"


def test_caution_signals_keep_their_evidence_references():
    data = LeadInput(
        evidence=[{"id": "e1", "source": "customer_message", "summary": "客户明确表示只是浏览"}],
        signals=[{"key": "explicitly_browsing_only", "evidence_ids": ["e1"]}],
    )
    result = assess_lead(data)
    assert result.caution_signals == ["explicitly_browsing_only"]
    assert result.caution_signal_evidence[0].evidence_ids == ["e1"]



def test_populated_facts_require_evidence_references():
    with pytest.raises(ValidationError):
        LeadInput(facts={"vehicle_model": "Model Y"})

    data = LeadInput(
        facts={"vehicle_model": "Model Y"},
        fact_evidence={"vehicle_model": ["e1"]},
        evidence=[{"id": "e1", "source": "customer_message", "summary": "客户明确询问Model Y"}],
    )
    assert assess_lead(data).evidence_coverage == 20


def test_fact_evidence_cannot_reference_missing_record():
    with pytest.raises(ValidationError):
        LeadInput(
            facts={"quantity": 4},
            fact_evidence={"quantity": ["not-found"]},
        )



def test_payment_received_is_a_later_stage_than_order_confirmed():
    data = LeadInput(
        evidence=[
            {"id": "e1", "source": "customer_message", "summary": "双方确认订单"},
            {
                "id": "e2",
                "source": "user_note",
                "summary": "卖方已核对对应订单的银行到账",
                "is_verified": True,
            },
        ],
        milestones=[
            {"key": "order_confirmed", "evidence_ids": ["e1"]},
            {"key": "payment_received", "evidence_ids": ["e2"]},
        ],
    )
    assert assess_lead(data).current_stage == "payment_received"


def test_decline_and_order_history_without_timestamps_is_flagged_as_ambiguous():
    data = LeadInput(
        evidence=[
            {"id": "e1", "source": "customer_message", "summary": "客户确认过订单"},
            {"id": "e2", "source": "customer_message", "summary": "客户后来表示不继续"},
        ],
        milestones=[
            {"key": "order_confirmed", "evidence_ids": ["e1"]},
            {"key": "explicitly_declined", "evidence_ids": ["e2"]},
        ],
    )
    result = assess_lead(data)
    assert result.current_stage == "needs_discovery"
    assert result.milestone_conflicts


def test_latest_decline_closes_previous_order_history():
    data = LeadInput(
        evidence=[
            {"id": "e1", "source": "customer_message", "summary": "客户确认订单"},
            {"id": "e2", "source": "customer_message", "summary": "客户明确取消采购"},
        ],
        milestones=[
            {
                "key": "order_confirmed",
                "evidence_ids": ["e1"],
                "observed_at": "2026-11-12T10:00:00+08:00",
            },
            {
                "key": "explicitly_declined",
                "evidence_ids": ["e2"],
                "observed_at": "2026-11-12T14:00:00+08:00",
            },
        ],
    )
    assert assess_lead(data).current_stage == "closed_lost"


def test_customer_reengagement_after_decline_reopens_latest_active_stage():
    data = LeadInput(
        evidence=[
            {"id": "e1", "source": "customer_message", "summary": "客户确认订单"},
            {"id": "e2", "source": "customer_message", "summary": "客户取消采购"},
            {"id": "e3", "source": "customer_message", "summary": "客户重新安排付款"},
        ],
        milestones=[
            {
                "key": "order_confirmed",
                "evidence_ids": ["e1"],
                "observed_at": "2026-11-12T10:00:00+08:00",
            },
            {
                "key": "explicitly_declined",
                "evidence_ids": ["e2"],
                "observed_at": "2026-11-12T14:00:00+08:00",
            },
            {
                "key": "payment_initiated",
                "evidence_ids": ["e3"],
                "observed_at": "2026-11-13T09:00:00+08:00",
            },
        ],
    )
    assert assess_lead(data).current_stage == "payment_pending"


def test_milestone_timestamp_requires_timezone_offset():
    with pytest.raises(ValidationError):
        LeadInput(
            evidence=[{"id": "e1", "source": "customer_message", "summary": "客户确认订单"}],
            milestones=[
                {
                    "key": "order_confirmed",
                    "evidence_ids": ["e1"],
                    "observed_at": "2026-11-12T10:00:00",
                }
            ],
        )
