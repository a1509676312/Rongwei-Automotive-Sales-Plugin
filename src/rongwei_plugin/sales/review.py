"""Seller-side conversation quality checks based on structured observations."""
from rongwei_plugin.models import SalesExecutionInput, SalesExecutionReview


def review_sales_execution(data: SalesExecutionInput) -> SalesExecutionReview:
    """Review only observations that the host AI can actually establish."""
    strengths: list[str] = []
    missed: list[str] = []
    risks: list[str] = []
    avoid: list[str] = []

    if data.customer_asked_a_specific_question is True:
        if data.seller_answered_that_question is True:
            strengths.append("销售人员回答了客户提出的具体问题。")
        elif data.seller_answered_that_question is False:
            missed.append("客户提出的具体问题尚未被明确回答，应先正面回应或说明需要核实。")
        else:
            missed.append("暂时无法确认销售是否回答了客户的具体问题，需要核对完整对话。")

    if data.seller_used_verified_information is True:
        strengths.append("本轮使用了已核实的信息。")
    elif data.seller_used_verified_information is False:
        missed.append("本轮关键产品或商务答复没有使用已核实资料支撑。")

    if data.seller_sent_relevant_material is True:
        strengths.append("已发送与客户当前问题相关的资料。")

    if data.seller_asked_one_clear_next_step is True:
        strengths.append("沟通中提出了明确的下一步。")
    elif data.seller_asked_one_clear_next_step is False:
        missed.append("缺少一个清楚、容易回答的下一步问题或动作。")

    if data.generic_followups_without_new_value:
        missed.append("存在没有新增信息或价值的重复跟进。")
        avoid.append("不要重复发送“有消息吗/考虑得怎样了”等泛泛催促。")

    if data.seller_made_unverified_claims:
        risks.append("发现待核实或无证据支持的销售承诺，必须先核实或删除。")
        avoid.extend(data.seller_made_unverified_claims)

    if data.response_delay_hours is not None and data.response_delay_hours >= 48:
        missed.append("回复间隔较长，可能错过客户当时的问题窗口；需结合客户所在时区和实际工作时间判断。")

    if data.seller_made_unverified_claims:
        rating = "high_risk"
        priority = "先撤回或核实所有无证据承诺，再继续推进客户。"
    elif missed:
        rating = "needs_improvement"
        priority = missed[0]
    elif len(strengths) >= 2:
        rating = "strong"
        priority = "保持当前有效做法，并继续推进客户已同意的下一步。"
    else:
        rating = "acceptable"
        priority = "现有记录不足以作全面评价；补充沟通事实后再判断销售动作质量。"

    if data.customer_asked_a_specific_question is True and data.seller_answered_that_question is not True:
        objective = "先解决客户提出的具体问题，避免直接跳到催单。"
    elif data.seller_asked_one_clear_next_step is False:
        objective = "基于客户当前阶段提出一个明确、容易回答的下一步。"
    else:
        objective = "跟进客户已确认的下一步，并核对是否出现新的阻碍。"

    return SalesExecutionReview(
        rating=rating,
        strengths=strengths,
        missed_opportunities=missed,
        priority_correction=priority,
        next_message_objective=objective,
        do_not_repeat=list(dict.fromkeys(avoid)),
        risk_notes=risks,
    )
