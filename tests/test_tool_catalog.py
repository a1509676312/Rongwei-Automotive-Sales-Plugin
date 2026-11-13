from rongwei_plugin.models import ObjectionRequest, SalesExecutionInput
from rongwei_plugin.sales.playbook import get_objection_plan
from rongwei_plugin.sales.review import review_sales_execution
from rongwei_plugin.tools.catalog import execute_tool, get_tool_catalog, registered_tool_names


def test_catalog_exposes_three_domain_tools():
    catalog = get_tool_catalog()
    assert len(catalog) == 3
    assert all(item["type"] == "function" for item in catalog)
    names = {item["function"]["name"] for item in catalog}
    assert names == set(registered_tool_names())


def test_lead_assessment_dispatch_returns_validated_result():
    result = execute_tool(
        "rw_assess_automotive_export_lead",
        {
            "evidence": [
                {"id": "e1", "source": "customer_message", "summary": "客户询问某车型的配置"}
            ],
            "signals": [{"key": "asks_technical_detail", "evidence_ids": ["e1"]}],
        },
    )
    assert result["evidence_score"] == 4
    assert result["score_is_close_probability"] is False
    assert result["current_stage"] == "needs_discovery"


def test_objection_tool_never_invents_a_price():
    result = execute_tool(
        "rw_get_objection_playbook",
        {"objection": "price_or_total_cost", "current_stage": "needs_discovery"},
    )
    assert "编造价格或价格区间" in result["avoid"]
    assert "比较口径统一" in result["recommended_sales_move"]


def test_review_flags_unverified_promises_as_high_risk():
    result = review_sales_execution(
        SalesExecutionInput(
            seller_made_unverified_claims=["保证七天到港"],
        )
    )
    assert result.rating == "high_risk"
    assert "先撤回或核实所有无证据承诺" in result.priority_correction


def test_review_does_not_treat_unobserved_actions_as_failures():
    result = review_sales_execution(SalesExecutionInput())
    assert result.rating == "acceptable"
    assert result.missed_opportunities == []


def test_review_detects_unanswered_customer_question():
    result = review_sales_execution(
        SalesExecutionInput(
            customer_asked_a_specific_question=True,
            seller_answered_that_question=False,
        )
    )
    assert result.rating == "needs_improvement"
    assert any("尚未被明确回答" in item for item in result.missed_opportunities)


def test_objection_plan_has_one_actionable_question():
    result = get_objection_plan(
        ObjectionRequest(objection="shipping_and_port", current_stage="commercial_process")
    )
    assert result.suggested_question
    assert "确认" in result.primary_goal


def test_dispatch_rejects_unknown_tool():
    try:
        execute_tool("send_whatsapp_message", {})
        assert False, "Unknown tools must not execute."
    except ValueError as exc:
        assert "Unknown Rongwei tool" in str(exc)
