# Rongwei Automotive Sales Plugin

> A model-agnostic automotive-export sales capability plugin for Chinese AI platforms.

**Status:** early development / API not yet released  
**Repository:** https://github.com/a1509676312/Rongwei-Automotive-Sales-Plugin

## What this project is

Rongwei Automotive Sales Plugin gives an AI host reusable automotive-export sales tools, structured workflows, evidence rules, and output schemas. The host AI performs language understanding and reasoning; this plugin supplies domain-specific sales operating logic and callable capabilities.

It is **not** an AI model, an AI engine, a CRM, a standalone chat bot, or a messaging-channel integration.

Users or their AI host explicitly provide advertising material, vehicle details, customer messages, chat screenshots, and optional prior context. The plugin helps the host AI analyze the opportunity and decide what to do next.

## Strict project boundaries

- No WhatsApp, Facebook, Instagram, Telegram, website-chat, or other channel connection; no message sending.
- No dependency on the user's previous sales-engine repositories, code, databases, deployments, or services.
- No required FastGPT, paid model, cloud account, or hosted database.
- No customer PII, real conversation screenshots, credentials, quotes, contracts, or private business records in this public repository.
- Replies are drafts only. The plugin never sends messages.
- The AI must not invent vehicle specifications, prices, stock, shipping schedules, delivery promises, payment status, or orders.
- Do not offer or fabricate a price unless the user supplies an authorized, verified price for the specific case.
- Keep each advertisement and vehicle context isolated. Mark uncertain vehicle/source attribution as unverified.
- Clearly separate user-provided facts, externally verified facts, inferences, and unknowns.

## Product goal: useful sales judgment, not superficial chat

The central acceptance goal is practical sales analysis that helps a real automotive-export salesperson move a deal forward. A useful analysis must:

1. Identify what the buyer is trying to purchase and for what purpose, using evidence.
2. Reconstruct the buyer's requirements: model, year, configuration, quantity, destination, intended use, timeline, and decision process.
3. Distinguish casual inquiry from a qualified opportunity without treating a price question as proof of buying intent.
4. Identify positive signals, objections, trust gaps, commercial risks, contradictions, and missing information.
5. State the current buying stage and explain why the evidence supports that stage.
6. Choose one concrete next objective and a proportionate next action.
7. Suggest a natural reply in the buyer's language, plus a concise Chinese explanation when useful.
8. Set a sensible follow-up trigger or timing, without encouraging spam or pressure.
9. Explain what information must be verified before making a claim or commitment.
10. Review stalled or lost opportunities by root cause and identify what the salesperson should change.

An intent score, when used, is a transparent evidence index—not a statistical probability that the deal will close. Evidence coverage and confidence must be reported separately.

## Initial Chinese-model integration scope

The project will focus on Chinese AI platforms, not every model worldwide. The first integration targets are:

- **DeepSeek** — first priority and initial compatibility target.
- **Qwen / Alibaba Cloud Model Studio (DashScope)**.
- **Doubao / Volcano Engine Ark**.
- **GLM / Zhipu BigModel**.
- **ERNIE / Baidu Qianfan**.

Each adapter must be tested against the current official endpoint, tool-call protocol, structured-output behavior, multimodal input support where relevant, and failure handling. A provider is not marked supported merely because it offers a chat API.

**Kimi / Moonshot** may be evaluated as a later candidate after its current official tool-calling contract is confirmed and tested. No unsupported compatibility claim is made in advance.

## Integration strategy

- Keep one canonical tool catalog and one canonical JSON schema.
- Expose tools through MCP and OpenAPI/REST.
- Provide provider-specific function/tool-call examples and adapters only where needed.
- Keep provider credentials outside the plugin and in environment variables or the host application's secret manager.
- Treat screenshots as host-supplied multimodal input or host-extracted text; the plugin does not connect to chat channels.
- Keep customer records local-first; encrypted local storage is optional until the desktop host bridge is installed and validated.
- Make external vehicle data, market research, and customs data optional extensions.

## Development principles

- Evidence before conclusions.
- No invented facts or unjustified certainty.
- Sales guidance must fit the buyer's actual stage and context.
- One clear next action is better than a generic list of follow-ups.
- Long conversations must be safely segmented and summarized without losing vehicle/ad attribution.
- All outputs must validate against versioned schemas.
- Automated tests must include realistic positive, negative, ambiguous, contradictory, and multilingual cases.
- No integration is considered complete until a real provider call and end-to-end tool execution have been tested.

## Planned delivery stages

1. Project foundation, schemas, domain rules, and test fixtures.
2. High-value automotive-export sales analysis tools and playbooks.
3. MCP and OpenAPI interfaces.
4. DeepSeek integration and end-to-end acceptance.
5. Qwen, Doubao, GLM, and Baidu Qianfan adapters.
6. Local-first encrypted customer vault, local companion/host bridges, and optional external data connectors.
7. Security review, regression tests, documentation, and release.

## Current implementation snapshot

Implemented on the development branch:
- Canonical business-context and analysis-result JSON Schemas.
- Evidence-led automotive export sales playbook and context preparation.
- Critical output checks for stage labels, intent evidence, fake close-probability fields, and prohibited auto-send flags.
- Six synthetic evaluation scenarios covering price-only inquiry, qualified interest, supplier comparison, payment concern, ad/vehicle conflict, and short silence.
- Initial DeepSeek function-calling adapter and Windows setup guide.
- Initial passphrase-encrypted local SQLite vault primitive, with workspace binding and tests.
- Local-first product requirements and privacy/security architecture documentation.

Local unit-test logic has been exercised during development. The local vault code has been committed but has **not** yet been run in the user’s Windows environment. The Harness integration and local filesystem bridge have **not** been validated against the installed Harness runtime. A live DeepSeek API call has **not** yet been verified; it requires the owner's API key and network access. Qwen, Doubao, GLM, and ERNIE adapters remain planned.

See [Sales Analysis Quality Specification](docs/sales-analysis-quality-spec.md) and [DeepSeek Integration Guide](docs/deepseek-integration.md).

## Development status

This repository is being built from scratch. Until code, tests, and live provider integration checks pass, features are considered planned or in development—not production-ready.
