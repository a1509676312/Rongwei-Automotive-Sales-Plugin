from datetime import datetime, timezone

from rongwei_plugin.workflow import experience_relevance, recommend_followup_delay


def test_customer_or_seller_commitment_takes_priority():
    promised = datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc)
    result = recommend_followup_delay("D", "initial", customer_promised_at=promised)
    assert result == promised


def test_same_country_experience_is_recommendation_not_fact():
    result = experience_relevance(
        record_country="Germany", requested_country="Germany", confidence="single_case"
    )
    assert result["may_recommend"] is True
    assert result["must_confirm_with_new_customer"] is True


def test_country_mismatch_is_not_reused():
    result = experience_relevance(
        record_country="Germany", requested_country="France", confidence="verified"
    )
    assert result["may_recommend"] is False
