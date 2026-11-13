# Rongwei Automotive Sales Plugin — Product Requirements v1

## Product

A reusable automotive-export sales capability plugin usable from multiple AI hosts and models. The AI host performs model reasoning; Rongwei supplies domain tools, evidence policy, schemas, and local customer context services.

## Users

Independent automotive-export salespeople and automotive-export companies. The plugin must not require a central Rongwei account or hosted customer database for its local-first mode.

## Core workflows

1. User supplies an advertisement, verified vehicle information, buyer/seller chat text, or a screenshot through the host's supported multimodal input.
2. Rongwei structures the case and associates it with the correct customer and advertisement only when evidence supports the association.
3. Host AI analyzes needs, buying stage, intent, objections, trust gaps, missing facts, salesperson performance, next action, and buyer-language reply draft.
4. User reviews and explicitly saves extracted facts and follow-up notes to the local vault. The product must distinguish confirmed facts from AI inferences and allow correction.
5. On a later session, user selects the customer and authorizes the minimum relevant history to be loaded into the model context.
6. Replies remain drafts. No channel connection or automatic sending is included.

## Required domain records

- Customer: stable local ID, name/company, phone, optional user-supplied contact fields, country/city, source, created/updated timestamps.
- Conversation: customer ID, message sequence, speaker, timestamp, original text, source reference, attachment reference.
- Advertisement: ad ID, text, vehicle candidates, source and verification state.
- Vehicle candidate: make/model/year/trim/condition/specifications, source and verification state.
- Requirement: destination country/port, model, quantity, use case, timeline, budget only when supplied.
- Follow-up: date, objective, result, next trigger, evidence references.
- Analysis: stage, intent level, evidence, confidence, objections, next objective/action, draft reply, created timestamp.
- Payment note: amount/currency/date/purpose only when explicitly supplied by the user; no payment processing.

## Privacy and data control

- Local-first by default; no central customer database.
- Encrypted local storage; passphrase never stored.
- Customer data never included in public repository, telemetry, crash reports, or analytics.
- No background sync or external backup without explicit opt-in.
- Before each AI call, disclose that selected context may be sent to the chosen AI provider; support data minimization and redaction.
- Never claim the AI provider does not retain or process submitted data unless current provider terms establish it.
- Local data is only read/written after an explicit user action or a clearly configured user-approved workflow.
- Provide local export, deletion, encrypted backup, restore, and lock controls.

## Cross-platform integration

- Canonical tool definitions and JSON schemas are host-neutral.
- MCP and OpenAPI are primary integration contracts.
- Harness receives a native bundle/UX adapter.
- Other hosts require their own thin adapters; unsupported platforms are not claimed compatible.
- Local storage access is capability-dependent. If an AI host cannot access local files or invoke a local companion service, it cannot use persistent local memory directly. Provide a local companion/service or host-specific bridge rather than silently moving data to a cloud.

## Non-goals

- No messaging-channel integrations or automatic message sending.
- No CRM employee-management suite.
- No model training or central model hosting.
- No invented prices, specifications, inventory, shipping, customs, payment, or delivery promises.

## Release gates

- Business scenario evaluation, including ambiguous, contradictory, multilingual, and long-conversation cases.
- Cross-model consistency against the same fixtures.
- Local vault encryption and recovery tests.
- Explicit model-provider data disclosure and minimization.
- Harness native installation and UI/tool invocation tested on the actual Harness version.
- No claim of universal AI compatibility without per-host conformance tests.
