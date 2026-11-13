"""Transparent lead-evidence scoring and stage derivation.

This is intentionally not a deal-close probability model. It scores observed buying
process evidence only. Missing information is not treated as a negative signal.
"""
from __future__ import annotations

from collections import defaultdict

from rongwei_plugin.models import LeadAssessment, LeadInput, ScoreBand, SignalScore

_SIGNAL_WEIGHTS: dict[str, int] = {
    "vehicle_requirements_specific": 8,
    "quantity_confirmed": 10,
    "destination_confirmed": 8,
    "buyer_role_confirmed": 6,
    "purchase_timeline_30d": 10,
    "purchase_timeline_90d": 6,
    "asks_technical_detail": 4,
    "asks_logistics_detail": 5,
    "asks_compliance_documents": 7,
    "asks_payment_process": 9,
    "requests_proforma": 12,
    "requests_contract": 14,
    "agrees_concrete_next_step": 8,
    "shares_business_identity": 5,
    "shares_import_documents": 9,
    "repeated_specific_engagement": 5,
    "explicitly_browsing_only": -7,
    "declines_core_qualification": -5,
    "repeated_unanswered_followups": -5,
    "contradictory_requirements": -4,
}
_NEAR_ORDER_MILESTONES = {
    "proforma_requested",
    "contract_requested",
    "payment_initiated",
    "payment_received",
    "order_confirmed",
}


def _stage(data: LeadInput) -> tuple[str, str]:
    milestones = {item.key for item in data.milestones}
    facts = data.facts
    if "order_confirmed" in milestones:
        return "order_confirmed", "客户已明确确认订单；该阶段来自明确记录，不由意向分数推断。"
    if "explicitly_declined" in milestones:
        return "closed_lost", "客户已明确拒绝继续推进；如后续重新联系，应作为新一轮机会重新评估。"
    if "payment_received" in milestones:
        return "payment_received", "已有用户核实或外部凭证支持的到账记录；仍需按订单流程核对后续履约事项。"
    if "payment_initiated" in milestones:
        return "payment_pending", "已有启动付款的明确记录；仍需核对实际到账，不能把付款意向当成收款。"
    if milestones.intersection({"proforma_requested", "contract_requested"}):
        return "order_process", "客户已进入形式发票或合同流程，需核对车型、数量、买卖双方和条款。"
    if milestones.intersection({"commercial_terms_discussed", "shipping_process_discussed"}):
        return "commercial_process", "双方已开始讨论商务或运输流程；尚不能据此认定订单成立。"
    if "solution_agreed" in milestones:
        return "solution_alignment", "客户已对方案表达认可，下一步应确认未解决的配置、合规和商务条件。"

    core = sum([
        bool(facts.vehicle_model or facts.vehicle_brand),
        bool(facts.quantity),
        bool(facts.destination_country),
        facts.purchase_timeline_days is not None,
        facts.buyer_type != "unknown",
    ])
    if core >= 3:
        return "qualified_opportunity", "车型、数量、目的地、采购时间或买家身份中已有至少三项得到确认。"
    if core > 0 or data.evidence:
        return "needs_discovery", "目前有初步信息，但关键采购条件仍不完整，需要先补齐需求。"
    return "new_inquiry", "当前没有足够的可追溯信息判断采购需求。"


def _band(score: int, has_order_milestone: bool) -> ScoreBand:
    if has_order_milestone:
        return ScoreBand(
            label="order_process",
            description="出现形式发票、合同或订单确认等明确推进节点；仍不等于付款到账或交易完成。",
        )
    if score >= 60:
        return ScoreBand(
            label="strong_buying_process",
            description="有多项具体采购行为证据，值得优先推进；这不是成交概率。",
        )
    if score >= 35:
        return ScoreBand(
            label="qualified_potential",
            description="已出现部分有效采购信号，但仍有关键条件或决策步骤待确认。",
        )
    if score >= 15:
        return ScoreBand(
            label="early_inquiry",
            description="有初步兴趣或零散采购信息，先做需求确认，不宜过早强推订单。",
        )
    return ScoreBand(
        label="insufficient_evidence",
        description="目前证据不足；不能仅凭询价、问候或单次回复认定为高意向客户。",
    )


def assess_lead(data: LeadInput) -> LeadAssessment:
    """Calculate a traceable evidence score and a conservative sales stage."""
    unique: dict[str, list[str]] = defaultdict(list)
    for observed in data.signals:
        for evidence_id in observed.evidence_ids:
            if evidence_id not in unique[observed.key]:
                unique[observed.key].append(evidence_id)

    # A 30-day purchase timeline subsumes the weaker 90-day signal.
    if "purchase_timeline_30d" in unique:
        unique.pop("purchase_timeline_90d", None)

    signal_scores: list[SignalScore] = []
    caution: list[str] = []
    caution_evidence: list[SignalScore] = []
    total = 0
    for key, evidence_ids in sorted(unique.items()):
        points = _SIGNAL_WEIGHTS[key]
        total += points
        if points < 0:
            caution.append(key)
            caution_evidence.append(
                SignalScore(key=key, points=points, evidence_ids=evidence_ids)
            )
        else:
            signal_scores.append(SignalScore(key=key, points=points, evidence_ids=evidence_ids))

    score = max(0, min(100, total))
    milestones = {item.key for item in data.milestones}
    has_order_milestone = bool(milestones.intersection(_NEAR_ORDER_MILESTONES))
    band = _band(score, has_order_milestone)

    facts = data.facts
    known_core = sum([
        bool(facts.vehicle_model or facts.vehicle_brand),
        bool(facts.quantity),
        bool(facts.destination_country),
        facts.purchase_timeline_days is not None,
        facts.buyer_type != "unknown",
    ])
    coverage = round(known_core / 5 * 100)
    if known_core >= 4 and len(data.evidence) >= 4:
        confidence = "high"
    elif known_core >= 2 and len(data.evidence) >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    stage, stage_reason = _stage(data)
    missing: list[str] = []
    if not (facts.vehicle_model or facts.vehicle_brand):
        missing.append("确认具体品牌、车型和年款")
    if not facts.quantity:
        missing.append("确认采购数量")
    if not facts.destination_country:
        missing.append("确认目的国家及目标港口")
    if facts.buyer_type == "unknown":
        missing.append("确认客户是进口商、经销商、车队采购方还是终端用户")
    if facts.purchase_timeline_days is None:
        missing.append("确认计划采购时间")
    if facts.decision_maker_known is not True:
        missing.append("确认对接人是否为决策人，以及是否还有其他审批人")

    if stage in {"order_process", "payment_pending"}:
        next_objective = "把订单主体、车型配置、数量、单证和付款节点逐项核实"
        next_action = "逐项确认未锁定的订单要素，并将已确认事项与待核实事项分开记录。"
    elif stage == "payment_received":
        next_objective = "确认收款凭证与订单对应关系，并推进已确认的履约准备"
        next_action = "将到账凭证、付款主体和对应订单核对一致，再按已确认的合同和交付流程推进。"
    elif stage in {"commercial_process", "solution_alignment"}:
        next_objective = "消除当前最大商务或交付障碍，争取客户确认下一步"
        next_action = "围绕客户当前最关心的一个问题给出有依据的答复，再提出一个明确、容易回答的下一步。"
    elif stage == "qualified_opportunity":
        next_objective = "补齐影响成交的关键采购条件"
        next_action = "优先确认缺失的采购时间、决策链或目的港，不要重复发送泛泛的产品介绍。"
    else:
        next_objective = "确认客户是否有真实、具体的采购计划"
        next_action = "先问清车型用途、数量、目的国家和采购时间；一次只聚焦最关键的缺口。"

    blockers = list(dict.fromkeys(data.blockers))
    if not blockers:
        blockers = ["尚未从输入中明确识别具体阻碍；需要结合客户原话确认。"]

    return LeadAssessment(
        case_ref=data.case_ref,
        advertisement_ref=data.advertisement_ref,
        evidence_score=score,
        band=band,
        confidence=confidence,
        evidence_coverage=coverage,
        current_stage=stage,
        stage_reason=stage_reason,
        positive_signals=signal_scores,
        caution_signals=caution,
        caution_signal_evidence=caution_evidence,
        blockers=blockers,
        missing_information=missing,
        next_objective=next_objective,
        next_action=next_action,
        reply_strategy=(
            "使用客户正在使用的语言，先回应其当前最重要的顾虑，再推动一个具体下一步；"
            "语气直接、自然，不堆砌产品卖点，不主动编造报价。"
        ),
        follow_up_trigger=(
            "按客户承诺的回复时间或已约定的下一步跟进；若未约定，先设置一次有内容的跟进，"
            "避免连续重复催促。"
        ),
        verification_before_commitment=[
            "车型、年款、配置必须与对应广告或可靠车型资料一致。",
            "价格、库存、运输周期、付款条件和交付承诺只能使用用户提供且已核实的信息。",
            "未收到可核验凭证前，不得把付款意向写成已付款。",
        ],
    )
