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
            {"id": "e4", "source": "customer_message", "summary": "说明一个月内采购"},
        ],
        signals=[
            {"key": "vehicle_requirements_specific", "evidence_ids": ["e1"]},
            {"key": "quantity_confirmed", "evidence_ids": ["e2"]},
            {"key": "destination_confirmed", "evidence_ids": ["e3"]},
            {"key": "purchase_timeline_30d", "evidence_ids": ["e4"]},
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
        evidence=[{"id": "e1", "source": "user_note", "summary": "卖方已核对银行到账记录"}],
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
