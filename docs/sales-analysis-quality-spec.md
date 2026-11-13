# Sales Analysis Quality Specification

**Status:** Draft for implementation  
**Version:** 1.0  
**Scope:** Automotive export sales analysis performed by a host AI using this plugin.

## 1. Quality objective

The plugin must help a salesperson make a better commercial decision from the evidence actually available. It must not merely paraphrase the buyer, assign a confident-looking score, or generate a generic follow-up message.

A successful analysis answers:

- What does this buyer appear to want, and what evidence supports that interpretation?
- How commercially qualified is this opportunity today?
- What is the most important unresolved obstacle?
- What should the salesperson do next, and what outcome should that action seek?
- What must be verified before the salesperson makes a factual or commercial commitment?

## 2. Required analysis sequence

Every full opportunity analysis follows this sequence. If information is missing, state the gap instead of inventing an answer.

1. **Conversation reconstruction**
   - Extract buyer and seller statements, questions, commitments, dates, quantities, vehicle references, and changes in position.
   - Preserve speaker attribution and chronology.
   - Separate explicit statements from interpretations.
2. **Advertisement and vehicle attribution**
   - Link the conversation to a specific ad/campaign/vehicle only when evidence supports the link.
   - Keep different ads and vehicle candidates isolated.
   - If attribution is ambiguous, mark it as unresolved and ask for the minimum clarification.
3. **Buyer requirement model**
   - Capture vehicle make/model, model year, trim/configuration, condition, quantity, destination country/port, use case, budget if volunteered, purchase timeline, and decision participants.
   - Use explicit values, unknown, or conflicting; never silently fill gaps.
4. **Buying-intent assessment**
   - Evaluate observable behaviors such as specific configuration questions, quantity, destination, shipping/import questions, payment-process questions, document requests, inspection requests, decision timing, and repeated engagement.
   - Treat generic greetings, isolated price requests, likes, and vague statements as weak evidence by themselves.
5. **Stage and momentum**
   - Assign a buying stage with evidence and identify whether momentum is advancing, unchanged, or weakening.
   - Do not infer a stage solely from the number of messages or elapsed time.
6. **Objection and risk diagnosis**
   - Identify explicit objections and likely concerns separately.
   - Consider price/value, trust, supplier credibility, vehicle specification, condition, logistics, import rules, payment risk, timing, and decision authority.
   - Rank the most consequential blocker; avoid listing every theoretical objection.
7. **Salesperson performance review**
   - Assess whether the salesperson answered the buyer's actual question, asked useful discovery questions, established credibility with evidence, controlled the conversation, handled objections, and secured a clear next step.
   - Point to the relevant message or missing action. Avoid vague judgments such as "follow up more".
8. **Next-move decision**
   - Choose one primary objective for the next interaction.
   - Recommend one concrete action and explain why it fits the current stage.
   - Include a fallback only when a meaningful alternative exists.
9. **Reply drafting**
   - Draft in the buyer's language when known.
   - Keep it natural, concise, commercially purposeful, and specific to the conversation.
   - Provide a Chinese explanation where useful.
   - Draft only: never send messages.
10. **Follow-up trigger**
    - Recommend a time or event-based trigger only when justified by context.
    - Avoid repeated pressure, spam, or artificial urgency.

## 3. Buying-stage taxonomy

Use a stage that best matches the evidence:

- `new_inquiry`: initial contact; requirements not yet established.
- `needs_discovery`: buyer is engaging, but important purchase requirements remain unknown.
- `qualified_interest`: a credible use case and meaningful requirements are emerging.
- `active_evaluation`: buyer is comparing options, configurations, suppliers, or commercial feasibility.
- `commercial_alignment`: buyer is discussing concrete terms, process, documents, logistics, or decision conditions.
- `decision_pending`: buyer has a defined decision or approval step outstanding.
- `ready_for_order`: buyer gives explicit, credible signals to proceed with order confirmation or formal process.
- `on_hold`: buyer explicitly pauses or gives a concrete external delay.
- `lost_or_unresponsive`: evidence supports loss or sustained non-response after appropriate follow-up; do not label a buyer lost based on a short silence.

Always include a short rationale and evidence references. A stage may be `unknown` when the input is insufficient.

## 4. Intent and confidence: no fake close probabilities

Do not present an uncalibrated model score as the statistical probability of closing.

If a numeric intent index is used:
- Label it clearly as an **evidence-based heuristic index**, not a close probability.
- Show the strongest positive and negative signals.
- Report evidence coverage and confidence separately.
- Explain what new evidence would materially change the assessment.
- Allow `insufficient_evidence` rather than forcing a score.

A later calibrated close-probability model would require a representative, consented, labeled historical dataset and validation. It is out of scope until such data exists.

## 5. Evidence and fact-safety contract

Each material claim must be classified as one of:

- `user_provided`: supplied directly by the user or conversation.
- `externally_verified`: checked against a named, traceable source.
- `inference`: a reasoned interpretation, with rationale and confidence.
- `unknown`: not established.
- `conflict`: sources or statements disagree.

Never invent or assume:
- Vehicle specifications, model year, trim, condition, certification, or availability.
- Price, discount, margin, payment status, or quotation validity.
- Shipping route, freight cost, delivery date, customs outcome, or import eligibility.
- Seller authority, buyer identity, purchase quantity, order status, or commitments.

The user has not authorized the assistant to offer prices by default. Do not generate a price or imply a quote exists unless the user provides an applicable, verified price and explicitly asks to use it.

## 6. Salesperson review rubric

Review the salesperson against the evidence in the conversation:

1. Responsiveness: did the answer address the buyer's actual question?
2. Discovery: did the salesperson uncover the missing decision-critical information?
3. Relevance: did the message connect the advertised vehicle's verified benefits to the buyer's stated need?
4. Trust: were claims supported without exaggeration?
5. Objection handling: was the real concern addressed rather than bypassed?
6. Conversation control: did the salesperson guide the exchange toward a useful next step?
7. Commitment: did the salesperson obtain a clear answer, document, decision, or agreed action where appropriate?
8. Follow-up discipline: was the timing and content proportionate?

For each weakness, provide:
- Evidence or missing evidence.
- Commercial consequence.
- Specific correction the salesperson can make next time.

Do not penalize a salesperson for facts they could not reasonably know from the supplied context.

## 7. Output contract

A full analysis should validate against the versioned schema and include, where applicable:

- `conversation_summary`
- `vehicle_and_ad_attribution`
- `buyer_requirements`
- `buying_stage`
- `intent_assessment`
- `positive_signals`
- `objections_and_risks`
- `missing_critical_information`
- `salesperson_review`
- `primary_next_objective`
- `recommended_next_action`
- `reply_draft`
- `reply_chinese_explanation`
- `follow_up_trigger`
- `fact_checks_required`
- `evidence_and_confidence`

Short tasks may return a smaller task-specific response, but must preserve fact/inference separation and the no-fabrication rules.

## 8. Evaluation and release gates

A provider or release must pass a shared test suite. The suite must include:

- Casual inquiry that looks superficially enthusiastic.
- A price-only inquiry with no other buying evidence.
- A buyer with concrete quantity, destination, and purchase timing.
- A buyer comparing several suppliers.
- A buyer raising trust or payment concerns.
- Contradictory vehicle model/year information.
- Multiple advertisements and vehicles in one conversation history.
- A buyer who is ready to proceed but has one critical unknown.
- Long conversation split into chunks with chronology preserved.
- Multilingual conversations and mixed-language messages.
- Sparse evidence where the correct result is uncertainty.
- A salesperson who gave an inaccurate or unsupported claim.
- A conversation where no reply should be sent yet and a clarification is the right next step.

Quality is judged on evidence accuracy, stage correctness, objection diagnosis, next-action usefulness, language naturalness, schema validity, and safety. A fluent reply alone is not a pass.

## 9. Provider compatibility scope

Initial provider targets:
1. DeepSeek (first end-to-end integration and acceptance target).
2. Qwen / Alibaba Cloud Model Studio.
3. Doubao / Volcano Engine Ark.
4. GLM / Zhipu BigModel.
5. ERNIE / Baidu Qianfan.

Kimi / Moonshot may be added after its current official API and tool-calling behavior are verified.

All providers must use the same canonical tool definitions, business rules, and output schemas. Provider-specific adapters may translate API request/response formats but must not change sales policy or business conclusions by design.

A provider is supported only after live API calls and the shared acceptance suite pass. Do not claim universal compatibility based on API similarity.

## 10. Non-goals

- No messaging-channel connection or automatic message sending.
- No CRM or employee-management system.
- No dependency on a particular model vendor or orchestration platform.
- No mandatory cloud database or paid external data source.
- No claim of statistically calibrated close prediction without validated data.
