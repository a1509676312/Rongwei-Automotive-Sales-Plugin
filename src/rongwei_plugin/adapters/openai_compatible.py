"""OpenAI-compatible chat/tool-call adapter for selected Chinese AI providers.

This adapter handles the common chat-completions tool-call round trip. Providers may
still require model-specific parameters or account/region configuration. DeepSeek's
thinking mode is treated specially so its reasoning_content is preserved by keeping
the original assistant SDK message in the conversation history.
"""
from __future__ import annotations

import os
from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any

from rongwei_plugin.tool_dispatch import execute_provider_tool_calls
from rongwei_plugin.tools.catalog import get_tool_catalog


@dataclass(frozen=True)
class ProviderSpec:
    api_key_env: str
    model_env: str
    base_url_env: str
    default_base_url: str
    thinking_mode: bool = False
    extra_body: dict[str, Any] | None = None


PROVIDERS: dict[str, ProviderSpec] = {
    "deepseek": ProviderSpec(
        api_key_env="DEEPSEEK_API_KEY",
        model_env="DEEPSEEK_MODEL",
        base_url_env="DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com",
        thinking_mode=True,
    ),
    "qwen": ProviderSpec(
        api_key_env="DASHSCOPE_API_KEY",
        model_env="QWEN_MODEL",
        base_url_env="QWEN_BASE_URL",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "doubao": ProviderSpec(
        api_key_env="ARK_API_KEY",
        model_env="DOUBAO_MODEL",
        base_url_env="ARK_BASE_URL",
        default_base_url="https://ark.cn-beijing.volces.com/api/v3",
    ),
    "glm": ProviderSpec(
        # First supported route: GLM models through Alibaba Cloud Model Studio.
        # The native Zhipu endpoint is a separate adapter candidate pending its own
        # current, non-deprecated chat-completions contract test.
        api_key_env="DASHSCOPE_API_KEY",
        model_env="GLM_MODEL",
        base_url_env="GLM_BASE_URL",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        extra_body={"tool_stream": True},
    ),
    "qianfan": ProviderSpec(
        api_key_env="QIANFAN_API_KEY",
        model_env="QIANFAN_MODEL",
        base_url_env="QIANFAN_BASE_URL",
        default_base_url="https://qianfan.baidubce.com/v2",
    ),
}


class ProviderConfigurationError(ValueError):
    """Raised when a provider is missing its API key or model identifier."""


def get_provider_config(provider: str) -> tuple[ProviderSpec, str, str, str]:
    """Return provider spec, API key, model ID and base URL without logging secrets."""
    key = provider.strip().lower()
    if key not in PROVIDERS:
        raise ProviderConfigurationError(
            f"Unsupported provider '{provider}'. Supported values: {', '.join(PROVIDERS)}."
        )
    spec = PROVIDERS[key]
    api_key = os.getenv(spec.api_key_env, "").strip()
    model = os.getenv(spec.model_env, "").strip()
    base_url = (
        os.getenv(spec.base_url_env, "").strip()
        or spec.default_base_url
    ).rstrip("/")
    missing = [
        variable
        for variable, value in ((spec.api_key_env, api_key), (spec.model_env, model))
        if not value
    ]
    if missing:
        raise ProviderConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}."
        )
    return spec, api_key, model, base_url


def run_tool_call_conversation(
    provider: str,
    messages: MutableSequence[Any],
    *,
    max_tool_rounds: int = 5,
    timeout_seconds: float = 90.0,
) -> str:
    """Run a bounded chat-completions/function-call loop and return final assistant text.

    The messages list is mutated in place to preserve the exact provider assistant
    message, including tool-call IDs and provider-specific metadata such as DeepSeek's
    reasoning_content. This function never sends a customer message to a channel.
    """
    if not 1 <= max_tool_rounds <= 12:
        raise ValueError("max_tool_rounds must be between 1 and 12.")
    if not 5 <= timeout_seconds <= 300:
        raise ValueError("timeout_seconds must be between 5 and 300.")

    spec, api_key, model, base_url = get_provider_config(provider)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderConfigurationError(
            'Install the "providers" extra: pip install -e ".[providers]".'
        ) from exc

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout_seconds,
        max_retries=2,
    )
    tools = get_tool_catalog()

    for _ in range(max_tool_rounds):
        request: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        if spec.extra_body:
            request["extra_body"] = dict(spec.extra_body)
        if spec.thinking_mode:
            request["reasoning_effort"] = "high"
            request["extra_body"] = {
                **request.get("extra_body", {}),
                "thinking": {"type": "enabled"},
            }

        response = client.chat.completions.create(**request)
        if not response.choices:
            raise RuntimeError(f"{provider} returned no choices.")

        assistant_message = response.choices[0].message
        # Keep the original SDK object; rebuilding from content alone could discard
        # tool_calls and, for DeepSeek thinking mode, reasoning_content.
        messages.append(assistant_message)

        tool_calls = assistant_message.tool_calls or []
        if not tool_calls:
            return assistant_message.content or ""

        messages.extend(execute_provider_tool_calls(tool_calls))

    raise RuntimeError(
        f"{provider} exceeded the configured limit of {max_tool_rounds} tool-call rounds."
    )
