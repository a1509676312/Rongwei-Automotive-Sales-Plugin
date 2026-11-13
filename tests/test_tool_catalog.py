from rongwei_plugin.tools.catalog import execute_tool, get_tool_catalog, registered_tool_names


def test_catalog_has_one_canonical_sales_tool():
    catalog = get_tool_catalog()
    assert len(catalog) == 1
    assert catalog[0]["type"] == "function"
    assert catalog[0]["function"]["name"] == registered_tool_names()[0]


def test_dispatch_validates_and_returns_json_safe_result():
    result = execute_tool(
        registered_tool_names()[0],
        {
            "evidence": [
                {"id": "e1", "source": "customer_message", "summary": "客户询问某车型的配置"}
            ],
            "signals": [{"key": "asks_technical_detail", "evidence_ids": ["e1"]}],
        },
    )
    assert result["evidence_score"] == 4
    assert result["score_is_close_probability"] is False
    assert result["current_stage"] == "needs_discovery"


def test_dispatch_rejects_unknown_tool():
    try:
        execute_tool("send_whatsapp_message", {})
        assert False, "Unknown tools must not execute."
    except ValueError as exc:
        assert "Unknown Rongwei tool" in str(exc)
