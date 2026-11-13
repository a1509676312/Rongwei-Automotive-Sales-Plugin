from rongwei_plugin.mcp_server import prepare_sales_analysis, validate_sales_analysis


def test_mcp_prepare_uses_shared_context_builder():
    result = prepare_sales_analysis({
        "case_id": "mcp-test",
        "language": "English",
        "conversation": [
            {"speaker": "buyer", "text": "I need two SUVs for Kenya."}
        ],
        "vehicles": [],
        "buyer_requirements": {"destination_country": "Kenya", "quantity": 2},
    })
    assert result["case_id"] == "mcp-test"
    assert result["conversation"][0]["speaker"] == "buyer"
    assert "sales_playbook" in result


def test_mcp_validate_uses_shared_validator():
    result = validate_sales_analysis({
        "buying_stage": "qualified_interest",
        "intent_assessment": {
            "level": "qualified",
            "rationale": "Buyer specified quantity and destination.",
            "evidence_coverage": "medium",
            "confidence": "medium",
        },
        "primary_next_objective": "Confirm vehicle requirements.",
        "recommended_next_action": "Ask for the preferred model and year.",
        "evidence_and_confidence": [
            {"claim": "Buyer needs two SUVs", "classification": "user_provided"}
        ],
    })
    assert result["valid"] is True
