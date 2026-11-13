import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'rongwei-automotive-sales-harness'
export const inject = ['tools']

const SALES_RULES = [
  'Analyze automotive-export buyer conversations from the evidence supplied by the user.',
  'Reconstruct the conversation chronologically and distinguish buyer, seller, and unknown speakers.',
  'Separate explicit facts, reasonable inferences, unknown information, and conflicting information.',
  'Assess buying stage and intent from observable behavior. A price-only inquiry alone is weak evidence.',
  'Identify the buyer’s strongest concern and the seller’s most consequential mistake, if any.',
  'Choose one primary next objective and one concrete next action.',
  'Keep advertisements and vehicle candidates separate. Never guess which advertisement a buyer refers to.',
  'Never invent vehicle specifications, model year, condition, stock, price, shipping, customs eligibility, payment, delivery, or order facts.',
  'Do not offer a price unless the user supplied an applicable verified price and explicitly authorized its use.',
  'Do not describe a heuristic score as a statistical probability of closing.',
  'When drafting a reply, use the buyer’s language, sound natural and concise, and explain the reply in Chinese.',
  'Replies are drafts only. Never send messages or claim a message was sent.'
]

const PLAYBOOK = {
  buying_stages: [
    'new_inquiry',
    'needs_discovery',
    'qualified_interest',
    'active_evaluation',
    'commercial_alignment',
    'decision_pending',
    'ready_for_order',
    'on_hold',
    'lost_or_unresponsive',
    'unknown'
  ],
  intent_levels: ['low', 'developing', 'qualified', 'high', 'insufficient_evidence'],
  positive_signals: [
    'specific model or configuration selection',
    'confirmed quantity',
    'destination country or port',
    'purchase timeline',
    'export documents or compliance questions',
    'payment process or order procedure',
    'decision-maker involvement',
    'specific next-step commitment'
  ],
  weak_signals: [
    'price-only inquiry',
    'generic expression of interest',
    'likes or short acknowledgements without a buying action'
  ],
  risk_signals: [
    'unverified vehicle or advertisement attribution',
    'unresolved specification or model-year conflict',
    'unclear buyer identity or decision authority',
    'payment-security concern',
    'supplier-trust concern',
    'import or homologation uncertainty',
    'seller repeatedly quoting without discovering requirements',
    'long silence after a concrete question'
  ],
  objection_categories: [
    'price_value',
    'supplier_trust',
    'vehicle_information',
    'shipping_logistics',
    'import_compliance',
    'payment_security',
    'purchase_timing',
    'decision_authority',
    'communication'
  ],
  salesperson_review: [
    'requirement discovery',
    'response relevance and speed',
    'vehicle and advertisement accuracy',
    'objection handling',
    'trust building with verifiable evidence',
    'control of negotiation next steps',
    'follow-up timing and purpose',
    'clarity of the closing request'
  ]
}

function asText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function prepareSalesBrief(args) {
  const conversation = asText(args.conversation)
  if (!conversation) {
    throw new Error('conversation is required and cannot be empty')
  }

  return JSON.stringify({
    plugin: 'Rongwei Automotive Sales',
    task: 'Analyze this automotive-export sales case using the evidence and playbook below. Return a practical sales analysis to the user.',
    case: {
      conversation,
      buyer_language: asText(args.buyer_language) || 'unknown',
      advertisement_context: asText(args.advertisement_context) || 'unknown',
      vehicle_information: asText(args.vehicle_information) || 'unknown',
      buyer_requirements: asText(args.buyer_requirements) || 'unknown',
      prior_follow_up_context: asText(args.prior_follow_up_context) || 'unknown'
    },
    required_analysis: [
      'conversation_summary',
      'buyer_requirements_and_missing_information',
      'vehicle_and_advertisement_attribution',
      'buying_stage',
      'intent_level_with_evidence_and_confidence',
      'strongest_positive_signals',
      'main_objections_and_risks',
      'salesperson_performance_review',
      'one_primary_next_objective',
      'one_concrete_next_action',
      'reply_draft_in_buyer_language_when_appropriate',
      'reply_chinese_explanation',
      'follow_up_trigger',
      'fact_checks_required'
    ],
    evidence_labels: ['user_provided', 'externally_verified', 'inference', 'unknown', 'conflict'],
    sales_rules: SALES_RULES,
    playbook: PLAYBOOK,
    final_instruction: 'Do not merely repeat the input. Perform the sales reasoning yourself after reading this tool result. If evidence is insufficient, say so and ask for the single most useful missing fact.'
  }, null, 2)
}

export function apply(ctx) {
  ctx.tools.register(defineTool({
    name: 'rongwei_sales_analyze',
    description: 'Rongwei 汽车出口销售分析工具。用户提供买家/卖家聊天文字、广告资料或跟进上下文时调用。工具会整理证据、业务规则和分析任务；随后你必须基于返回内容完成销售阶段、意向、异议、销售表现、下一步成交策略和客户语言回复草稿。不得编造价格、车型参数、库存、物流或付款承诺，不得发送消息。',
    parameters: {
      conversation: {
        type: 'string',
        required: true,
        description: '完整聊天记录文字，尽量保留买家/卖家身份和先后顺序。可由用户从截图转写或粘贴。'
      },
      buyer_language: {
        type: 'string',
        required: false,
        description: '买家使用的语言；未知时留空。'
      },
      advertisement_context: {
        type: 'string',
        required: false,
        description: '对应广告、广告文案或广告编号；不确定时留空。'
      },
      vehicle_information: {
        type: 'string',
        required: false,
        description: '用户已提供或核实的车型、年款、配置等；禁止猜测。'
      },
      buyer_requirements: {
        type: 'string',
        required: false,
        description: '已知国家、港口、数量、预算、采购时间、用途等需求。'
      },
      prior_follow_up_context: {
        type: 'string',
        required: false,
        description: '此前沟通、跟进时间和客户承诺；没有则留空。'
      }
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }]
    },
    async execute(args) {
      return prepareSalesBrief(args)
    }
  }))
}
