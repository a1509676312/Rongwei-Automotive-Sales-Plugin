"""Minimal DeepSeek tool-call integration example.

This example is a host application: DeepSeek chooses tools, while Rongwei executes
the business functions locally. It uses the thinking-mode tool-call flow and keeps
the original assistant message in history so reasoning_content/tool_calls are retained.

Environment:
    DEEPSEEK_API_KEY   required
    DEEPSEEK_MODEL     required; choose a currently enabled model in your account
    DEEPSEEK_BASE_URL  optional; defaults to https://api.deepseek.com

Install:
    pip install -e ".[deepseek]"
Run:
    python examples/deepseek_tool_call.py
"""
from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI
from rongwei_plugin.tool_dispatch import execute_provider_tool_calls
from rongwei_plugin.tools.catalog import get_tool_catalog


def main() -> None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    model = os.getenv("DEEPSEEK_MODEL")
    if not api_key or not model:
        raise SystemExit("Set DEEPSEEK_API_KEY and DEEPSEEK_MODEL before running.")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    tools = get_tool_catalog()
    prompt_path = (
        Path(__file__).resolve().parents[1]
        / "prompts"
        / "automotive-export-sales-director.md"
    )
    if not prompt_path.is_file():
        raise SystemExit(f"Sales-director prompt file not found: {prompt_path}")
    system_prompt = prompt_path.read_text(encoding="utf-8")
    messages: list[object] = [
        {"role": "system", "content": system_prompt},
    ]

    customer_material = input("Paste customer chat text (do not include real phone/email): ").strip()
    if not customer_material:
        raise SystemExit("No customer material was provided.")

    messages.append({
        "role": "user",
        "content": (
            "请分析下面这段汽车出口客户沟通。按系统要求提取事实和证据，"
            "必要时调用 Rongwei 销售工具。不要编造，不要自动发送回复。\n\n"
            + customer_material
        ),
    })

    max_tool_rounds = 5
    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        assistant_message = response.choices[0].message

        # Important for DeepSeek thinking-mode tool calls:
        # append the original SDK message instead of rebuilding it and accidentally
        # dropping reasoning_content or provider metadata.
        messages.append(assistant_message)

        tool_calls = assistant_message.tool_calls or []
        if not tool_calls:
            print(assistant_message.content or "")
            return

        messages.extend(execute_provider_tool_calls(tool_calls))

    raise SystemExit(
        "Tool-call round limit reached. Review the conversation or reduce the task scope."
    )


if __name__ == "__main__":
    main()
