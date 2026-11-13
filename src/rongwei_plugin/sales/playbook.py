"""Practical objection-handling playbooks for automotive export sales."""
from rongwei_plugin.models import ObjectionKey, ObjectionPlan, ObjectionRequest

_PLANS: dict[ObjectionKey, dict[str, object]] = {
    "vehicle_fit": {
        "primary_goal": "确认客户需求与当前车型是否真正匹配。",
        "information_to_verify": ["客户实际用途", "必须满足的车型/配置条件", "可接受的年款或替代车型"],
        "recommended_sales_move": "把客户的必选条件与已核实车型资料逐项对照，只指出确定匹配和需要核实的差异。",
        "suggested_question": "Which exact features are essential for your use, so I can check the right version for you?",
        "reply_guidance": "先确认用途和必选配置，再给有来源的车型对比；不要只重复广告卖点。",
        "avoid": ["未经核实就说完全匹配", "把不同年款或配置混为一谈", "用无关卖点转移客户问题"],
    },
    "price_or_total_cost": {
        "primary_goal": "弄清客户比较的是车辆价格还是落地总成本，并确认比较条件一致。",
        "information_to_verify": ["客户比较的车型、年款和配置", "目的国家及港口", "客户所说价格是否包含运输、保险、税费或其他费用"],
        "recommended_sales_move": "不要先降价或报一个未经授权的数字；先把比较口径统一，确认客户最在意的成本项。",
        "suggested_question": "Are you comparing the vehicle price only, or the total cost to your destination port?",
        "reply_guidance": "认可客户对成本的关注，明确比较口径，再确认目的港和费用范围；只有用户提供并授权的真实价格才能使用。",
        "avoid": ["编造价格或价格区间", "擅自承诺折扣", "把不含运费的价格说成到港价", "贬低竞争对手"],
    },
    "shipping_and_port": {
        "primary_goal": "确认运输方案是否可行，以及客户担心的是时间、费用还是目的港安排。",
        "information_to_verify": ["目的国家和港口", "客户期望到货时间", "车型尺寸/数量是否影响运输方案", "运输信息来源和更新时间"],
        "recommended_sales_move": "先确认目的港和交付要求，再向可靠物流来源核实；未核实前只说明需要确认。",
        "suggested_question": "Which destination port should we check for your shipment?",
        "reply_guidance": "不要泛泛承诺运输，先问清港口和数量，再核实船期、费用及适用条件。",
        "avoid": ["编造海运费、船期或运输天数", "保证清关或交付日期", "把历史运费当作当前报价"],
    },
    "import_compliance": {
        "primary_goal": "明确进口国法规、认证和文件要求，避免车型无法合规进口。",
        "information_to_verify": ["目的国家", "车型和年款", "客户所需认证/标准", "是否需要右舵/左舵或特殊配置", "法规信息的官方来源和有效日期"],
        "recommended_sales_move": "先识别适用国家和具体车型，再核对官方法规或可信专业来源；把已核实与待确认事项分开。",
        "suggested_question": "Which country will the vehicle be registered in, and do you have a specific import or certification requirement?",
        "reply_guidance": "把法规核实当成成交前的重要步骤，主动说明需要按具体车型和国家确认。",
        "avoid": ["声称一定可以进口或上牌", "用其他国家法规替代", "引用过期或无来源的认证要求"],
    },
    "payment_security": {
        "primary_goal": "解决付款安全疑虑，并确保付款流程可核验。",
        "information_to_verify": ["付款方和合同主体", "正式合同/发票信息", "收款账户归属和核验方式", "双方已确认的付款节点"],
        "recommended_sales_move": "通过正式文件和可核验的公司/银行信息说明流程；付款条款只能引用用户已批准的版本。",
        "suggested_question": "Would it help if I first clarify the company details and the formal payment process?",
        "reply_guidance": "先建立流程透明度，不催促付款；让客户有机会核对主体和正式文件。",
        "avoid": ["承诺未经批准的付款方式或账期", "要求向个人账户付款", "把付款截图当成到账凭证"],
    },
    "supplier_trust": {
        "primary_goal": "降低客户对供应商真实性、车辆状态和履约能力的顾虑。",
        "information_to_verify": ["客户具体担忧", "可公开展示的公司资料", "当前车辆资料/检查记录", "是否获得授权分享案例或证明"],
        "recommended_sales_move": "针对客户提出的具体担忧提供可验证材料，例如公司主体信息、当前车辆视频或检查流程。",
        "suggested_question": "What would you need to verify first before feeling comfortable moving forward with us?",
        "reply_guidance": "不要空口强调可靠，使用真实、可核验、且获准分享的资料建立信任。",
        "avoid": ["编造客户案例、出口记录或资质", "使用未经授权的其他客户资料", "给出无法兑现的保证"],
    },
    "decision_process": {
        "primary_goal": "确认决策链和采购流程，避免只与信息收集者反复沟通。",
        "information_to_verify": ["当前联系人职责", "最终决策人", "是否有合伙人/财务/采购审批", "内部确认时间"],
        "recommended_sales_move": "礼貌确认谁会参与最终选择，并提供便于内部转发的简短、事实型资料。",
        "suggested_question": "Will you make the final vehicle decision, or will another partner or purchasing manager review it with you?",
        "reply_guidance": "不要质疑客户权限；自然了解参与决策的人和下一步审批时间。",
        "avoid": ["绕过客户擅自联系其同事", "要求不必要的个人信息", "把客户暂时无法决定视为拒绝"],
    },
    "purchase_timing": {
        "primary_goal": "判断客户当前是收集资料、准备采购，还是有明确采购窗口。",
        "information_to_verify": ["期望采购时间", "时间是否受项目/资金/进口许可影响", "客户需要在该日期前完成什么"],
        "recommended_sales_move": "把时间问题落到客户自己的计划节点，而不是制造虚假库存或涨价紧迫感。",
        "suggested_question": "When are you planning to make the purchase decision, and is there a deadline we should work around?",
        "reply_guidance": "按客户计划安排资料和跟进，不以虚假稀缺推动成交。",
        "avoid": ["制造虚假限时优惠", "声称库存即将售罄但没有证据", "频繁催促尚未准备好的客户"],
    },
    "configuration_uncertainty": {
        "primary_goal": "确认双方讨论的是同一车型年款和同一配置版本。",
        "information_to_verify": ["完整车型名称和年款", "配置代码/关键差异", "动力/续航/驱动/座椅等客户在意项目", "资料来源"],
        "recommended_sales_move": "建立一份客户必选配置清单，与可靠资料逐项核对后再答复。",
        "suggested_question": "Which two or three configuration features are must-haves for you?",
        "reply_guidance": "只比较可证实的配置；存在版本差异时明确说明。",
        "avoid": ["凭图片猜年款或配置", "将选装配置当作标配", "用相似车型参数填补空缺"],
    },
    "competitor_comparison": {
        "primary_goal": "弄清客户具体在比较什么，并用同口径事实建立差异。",
        "information_to_verify": ["对比车型及配置", "报价是否含相同费用", "售后/文件/运输条件", "客户最重视的决策因素"],
        "recommended_sales_move": "把比较限定在客户关心的两三项，提供有来源的差异，不攻击竞争对手。",
        "suggested_question": "Which factors matter most in your comparison: vehicle specification, export documents, logistics, or supplier reliability?",
        "reply_guidance": "先找出比较标准，再提供事实，不做未经证实的竞品评价。",
        "avoid": ["贬低其他供应商", "虚构竞品缺点", "把不同版本的参数直接对比"],
    },
    "unknown": {
        "primary_goal": "先确定客户现在最关心的问题，避免盲目推销。",
        "information_to_verify": ["客户首要目标", "具体车型或使用场景", "采购计划是否明确"],
        "recommended_sales_move": "回到客户最近一次明确表达，问一个最能推进判断的问题。",
        "suggested_question": "What is the main thing you need to confirm before deciding on the vehicle?",
        "reply_guidance": "简洁回应并提出一个开放但具体的问题。",
        "avoid": ["一次抛出多个问题", "机械发送车型目录", "假设客户的预算或采购计划"],
    },
}


def get_objection_plan(request: ObjectionRequest) -> ObjectionPlan:
    """Return a practical, fact-safe strategy for one primary objection."""
    plan = _PLANS[request.objection]
    return ObjectionPlan(objection=request.objection, **plan)
