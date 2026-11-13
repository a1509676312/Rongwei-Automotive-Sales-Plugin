# Model-agnostic integration

Rongwei's business logic is provider-neutral. The host AI performs language reasoning; Rongwei supplies the same automotive-export playbook, normalized case context, and validation rules regardless of model vendor.

## Supported integration contract

The canonical contract is:
- JSON input: `schemas/business-context.schema.json`
- JSON output: `schemas/sales-analysis-result.schema.json`
- Tool: `prepare_sales_analysis`
- Validator: `validate_sales_analysis`

A model/provider is not declared compatible merely because it can send chat text. It must be able to invoke the tools (directly or through an adapter), handle the returned structured content, produce the canonical result, and pass the shared evaluation cases.

## MCP (recommended portable integration)

MCP is the preferred cross-platform integration because compatible hosts can connect to the same local or remote MCP server without a provider-specific API key in Rongwei.

Install:
```powershell
pip install -e ".[mcp]"
```

Run locally:
```powershell
python -m rongwei_plugin.mcp_server
```

The server uses stdio transport. Configure the host application's MCP client to launch the command in the project environment. Exact UI/configuration steps vary by host.

The MCP server does not call DeepSeek, Qwen, Doubao, GLM, ERNIE, or any other model. The connected host model performs the reasoning and pays its own model-token costs.

## OpenAI-compatible tool calling

For hosts that expose an OpenAI-compatible function/tool-calling API, use the canonical tool definitions and schemas as the function parameters. Provider adapters should remain thin: translate tool-call envelopes only, then call the same Python business functions. Do not fork sales rules per provider.

## REST / OpenAPI

`openapi/rongwei-sales.openapi.yaml` describes an optional REST interface for platforms that cannot run MCP but can call HTTP tools. A deployment wrapper can expose these operations; the public plugin repository does not require a hosted server.

## Host compatibility

Potential integration targets include DeepSeek Harness, Qwen-compatible agents, Doubao/Volcano Engine agents, GLM agents, ERNIE/Qianfan agents, and other MCP- or function-tool-capable hosts. Compatibility must be verified per host version and model/tool-call capability. No claim is made that every model or application supports MCP, image input, or function calling.

## Images and screenshots

Image understanding is performed by the host model if it supports image input. If the host cannot pass images to the tool, it must first extract the visible conversation text and preserve speaker/order attribution. Rongwei itself does not connect to messaging channels or upload images to external services.

## Security

- Keep provider API keys in the host's secret manager or local environment.
- Never put credentials in tool arguments, source code, test fixtures, or public Git.
- Use only anonymized/synthetic conversations in public tests.
- Do not expose a public unauthenticated REST endpoint containing customer data.
- Replies are drafts only; there is no message-sending tool.
