"""Shared integration example for the first five Chinese AI providers.

Set the selected provider's API key and model ID environment variables, then run:
    python examples/chinese_ai_tool_call.py deepseek
    python examples/chinese_ai_tool_call.py qwen
    python examples/chinese_ai_tool_call.py doubao
    python examples/chinese_ai_tool_call.py glm
    python examples/chinese_ai_tool_call.py qianfan

The example sends customer material only to the provider whose API key is configured.
Do not paste phone numbers, email addresses, or other unnecessary personal information.
"""
from __future__ import annotations

import sys
from pathlib import Path

from rongwei_plugin.adapters.openai_compatible import (
    PROVIDERS,
    ProviderConfigurationError,
    run_tool_call_conversation,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: python {Path(__file__).name} <{'|'.join(PROVIDERS)}>")

    provider = sys.argv[1].lower()
    if provider not in PROVIDERS:
        raise SystemExit(f"Unsupported provider. Choose: {', '.join(PROVIDERS)}")

    prompt_path = (
        Path(__file__).resolve().parents[1]
        / "prompts"
        / "automotive-export-sales-director.md"
    )
    system_prompt = prompt_path.read_text(encoding="utf-8")
    material = input("Paste the customer's chat text (remove personal contact details): ").strip()
    if not material:
        raise SystemExit("No customer material was provided.")

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "请分析下面的汽车出口客户沟通，提取事实与证据，必要时调用 Rongwei 工具。"
                "请给出成交障碍、下一步策略和客户语言回复草稿；不得编造或自动发送。\n\n"
                + material
            ),
        },
    ]

    try:
        result = run_tool_call_conversation(provider, messages)
    except ProviderConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
    except Exception as exc:
        raise SystemExit(
            f"Provider call failed ({type(exc).__name__}). Check model ID, endpoint, "
            "account permissions, rate limits, and API quota."
        ) from exc

    print(result)


if __name__ == "__main__":
    main()
