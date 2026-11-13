"""Seller-side conversation quality checks based on structured observations."""
from rongwei_plugin.models import SalesExecutionInput, SalesExecutionReview


def review_sales_execution(data: SalesExecutionInput) -> SalesExecutionReview:
    strengths: list[str] = []
    missed: list[str] = []
    risks: list[str] = []
    avoid: list[str] = []

    if data.seller_answered_that_question and data.customer_asked_a_specific_question:
        strengths.append("销售人员回答了客户提出的具体问题。")
    elif data.customer_asked_a_specific_question:
        missed.append("客户提出的具体问题尚未被明确回答，应先正面回应或说明需要核实。")

    if data.seller_used_verified_information:
        strengths.append("本轮使用了已核实的信息。")
    else:
        missed.append("没有看到使用已核实资料支撑关键产品或商务答复的证据。")

    if data.seller_sent_relevant_material:
        strengths.append("已发送与客户当前问题相关的资料。")

    if data.seller_asked_one_clear_next_step:
        strengths.append("沟通中提出了明确的下一步。")
    else:
        missed.append("缺少一个清楚、容易回答的下一步问题或动作。")

    if data.generic_followups_without_new_value:
        missed.append("存在没有新增信息或价值的重复跟进。")
        avoid.append("不要重复发送“有消息吗/考虑得怎样了”等泛泛催促。")

    if data.seller_made_unverified_claims:
        risks.append("发现待核实或无证据支持的销售承诺，必须先核实或删除。")
        avoid.extend(data.seller_made_unverified_claims)

    if data.response_delay_hours is not None and data.response_delay_hours >= 48:
        missed.append("回复间隔较长，可能错过客户当时的问题窗口；需结合客户所在时区和实际工作时间判断。")

    if data.seller_message_summary:
        # The supplied summary is context only; this rule engine does not infer intent from prose.
        pass

    if data.seller_made_unverified_claims:
        rating = "high_risk"
        priority = "先撤回或核实所有无证据承诺，再继续推进客户。"
    elif missed:
        rating = "needs_improvement"
        priority = missed[0]
    elif strengths:
        rating = "strong"
        priority = "保持当前有效做法，并继续推进客户已同意的下一步。"
    else:
        rating = "acceptable"
        priority = "补充可追溯的沟通事实后再作销售质量判断。"

    if data.customer_asked_a_specific_question and not data.seller_answered_that_question:
        objective = "先解决客户提出的具体问题，避免直接跳到催单。"
    elif not data.seller_asked_one_clear_next_step:
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
