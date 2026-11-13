# Architecture

## Design principle

The host AI is the reasoning model. Rongwei is the automotive-export domain toolset, contract, and workflow layer. The plugin must not require a particular model provider to execute its domain logic.

## Layers

1. **Host input** — user-provided ad material, vehicle details, customer messages/screenshots, and optional context.
2. **Provider adapter** — converts canonical tool definitions to a Chinese provider's current function/tool-call contract.
3. **Canonical contracts** — Pydantic input/output models and versioned JSON Schemas.
4. **Domain services** — evidence validation, lead-evidence scoring, stage derivation, next-action constraints, and fact-check gates.
5. **Transport adapters** — MCP and OpenAPI/REST.
6. **Optional integrations** — external vehicle sources, market/customs data, customer-context persistence, and file/image processing.

## Data flow

1. Host AI receives user material directly.
2. Host AI extracts candidate facts and short evidence references; uncertain fields remain unknown.
3. Host AI invokes Rongwei tools using canonical structured arguments.
4. The plugin validates the schema and evidence references, applies deterministic business rules, and returns a structured result.
5. Host AI explains the result and drafts a customer-language reply.
6. The user reviews and sends the reply outside the plugin.

## Hard boundaries

- No channel credentials, message ingestion, or automated sending.
- No dependence on a prior repository, database, deployment, or sales engine.
- No storage of direct customer identifiers in public repo fixtures or default logs.
- No model vendor is allowed to override the evidence and truthfulness rules.
- An unavailable external source must produce an explicit unavailable/unknown result, never fabricated data.

## Model scope

Initial integration targets are DeepSeek, Qwen, Doubao, GLM, and Baidu Qianfan/ERNIE. DeepSeek is first. Every adapter is a thin translation layer around the same tool catalog and schemas. Provider support is tracked per feature and version; it is not inferred from an OpenAI-compatible chat endpoint alone.

Kimi is a later candidate until the current official custom tool-calling contract has been confirmed and exercised in tests.

## Long-context handling

- Preserve advertisement reference and vehicle identity on every summarized segment.
- Chunk conversations by turn boundaries, not arbitrary mid-message cuts.
- Preserve dates, currency codes, units, country/port, vehicle model/year/configuration, and explicit commitments.
- Summaries must keep source references and distinguish facts from inferences.
- Never merge two ads or two vehicle models just because they appear in the same chat.

## Security

- Credentials are provided at runtime through environment variables or the host's secret manager.
- Never commit .env or API keys.
- Redact direct identifiers from logs.
- Add authentication and rate limits before exposing a hosted deployment.
- Customer context persistence is optional and must be tenant-isolated with read/update/delete controls.
