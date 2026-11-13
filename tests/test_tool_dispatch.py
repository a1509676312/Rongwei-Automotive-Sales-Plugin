import json

import pytest

from rongwei_plugin.tool_dispatch import ToolCallDispatchError, execute_provider_tool_calls


def test_dispatch_provider_function_call_and_keep_original_call_id():
    result = execute_provider_tool_calls([
        {
            "id": "call-123",
            "type": "function",
            "function": {
                "name": "rw_assess_automotive_export_lead",
                "arguments": json.dumps({
                    "evidence": [
                        {"id": "e1", "source": "customer_message", "summary": "客户问具体配置"}
                    ],
                    "signals": [
                        {"key": "asks_technical_detail", "evidence_ids": ["e1"]}
                    ],
                }),
            },
        }
    ])
    assert result[0]["role"] == "tool"
    assert result[0]["tool_call_id"] == "call-123"
    assert result[0]["name"] == "rw_assess_automotive_export_lead"
    body = json.loads(result[0]["content"])
    assert body["ok"] is True
    assert body["result"]["evidence_score"] == 4


def test_unknown_tool_returns_safe_error_without_echoing_arguments():
    private_value = "private customer phone 555-0100"
    result = execute_provider_tool_calls([
        {
            "id": "call-unknown",
            "function": {
                "name": "send_whatsapp_message",
                "arguments": json.dumps({"phone": private_value}),
            },
        }
    ])
    body = json.loads(result[0]["content"])
    assert body == {"ok": False, "error": "unknown_tool"}
    assert private_value not in result[0]["content"]


def test_malformed_arguments_return_safe_error():
    result = execute_provider_tool_calls([
        {
            "id": "call-bad",
            "function": {
                "name": "rw_assess_automotive_export_lead",
                "arguments": "{not-json",
            },
        }
    ])
    body = json.loads(result[0]["content"])
    assert body["ok"] is False
    assert body["error"] == "invalid_tool_arguments"


def test_duplicate_call_ids_are_rejected():
    call = {
        "id": "duplicate",
        "function": {"name": "rw_get_objection_playbook", "arguments": '{"objection":"unknown"}'},
    }
    with pytest.raises(ToolCallDispatchError):
        execute_provider_tool_calls([call, call])


def test_call_batch_limit_is_enforced():
    calls = [
        {
            "id": f"call-{index}",
            "function": {"name": "rw_get_objection_playbook", "arguments": '{"objection":"unknown"}'},
        }
        for index in range(3)
    ]
    with pytest.raises(ToolCallDispatchError):
        execute_provider_tool_calls(calls, max_calls=2)
