from rongwei_plugin.sales.analysis import build_sales_analysis_context, validate_analysis_result


def test_context_preserves_speakers_and_vehicle_candidates():
    brief = build_sales_analysis_context({
        "language": "en",
        "conversation": [
            {"speaker": "buyer", "text": "I need two SUVs for Kenya."},
            {"speaker": "seller", "text": "Which model are you considering?"},
        ],
        "vehicles": [{"vehicle_id": "ad-1", "make": "Example", "model": "SUV", "verification_status": "user_provided"}],
    })
    assert brief["conversation"][0]["speaker"] == "buyer"
    assert brief["conversation"][1]["speaker"] == "seller"
    assert brief["vehicle_candidates"][0]["vehicle_id"] == "ad-1"
    assert "Do not offer or fabricate a price" in " ".join(brief["analysis_rules"])


def test_context_marks_missing_source_as_unknown():
    brief = build_sales_analysis_context({"conversation": [], "vehicles": []})
    assert brief["source"]["source_confidence"] == "unknown"


def test_valid_result_passes():
    result = {
        "buying_stage": "needs_discovery",
        "intent_assessment": {
            "level": "developing",
            "heuristic_index": 35,
            "rationale": "The buyer stated a use case but no purchase timing.",
            "evidence_coverage": "medium",
            "confidence": "medium",
        },
        "primary_next_objective": "Confirm destination and required vehicle configuration.",
        "recommended_next_action": "Ask the buyer which configuration and destination port they need.",
        "evidence_and_confidence": [
            {"claim": "Buyer needs two SUVs", "classification": "user_provided", "confidence": "high"}
        ],
    }
    assert validate_analysis_result(result)["valid"] is True


def test_rejects_fake_close_probability_and_auto_send():
    result = {
        "buying_stage": "ready_for_order",
        "intent_assessment": {
            "level": "high",
            "heuristic_index": 90,
            "close_probability": 0.9,
            "rationale": "Unsupported prediction",
            "evidence_coverage": "low",
            "confidence": "low",
        },
        "primary_next_objective": "Get order confirmation.",
        "recommended_next_action": "Ask for written confirmation.",
        "message_sent": True,
    }
    check = validate_analysis_result(result)
    assert check["valid"] is False
    assert any("close probability" in error for error in check["errors"])
    assert any("Automatic message" in error for error in check["errors"])


def test_rejects_invalid_stage_and_empty_next_action():
    check = validate_analysis_result({
        "buying_stage": "hot",
        "intent_assessment": {
            "level": "high", "rationale": "x",
            "evidence_coverage": "medium", "confidence": "medium",
        },
        "primary_next_objective": "",
        "recommended_next_action": " ",
    })
    assert check["valid"] is False


def test_rejects_unknown_intent_level():
    check = validate_analysis_result({
        "buying_stage": "needs_discovery",
        "intent_assessment": {
            "level": "very_hot",
            "rationale": "Unsupported label",
            "evidence_coverage": "medium",
            "confidence": "medium",
        },
        "primary_next_objective": "Clarify requirements.",
        "recommended_next_action": "Ask one relevant question.",
    })
    assert check["valid"] is False
    assert any("intent_assessment.level" in error for error in check["errors"])


def test_synthetic_sales_case_pack_has_six_distinct_cases():
    import json
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "sales_cases.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert len(data["cases"]) == 6
    assert len({case["case_id"] for case in data["cases"]}) == 6
    assert any(case["expected"]["buying_stage"] == "new_inquiry" for case in data["cases"])
    assert any(case["expected"]["buying_stage"] == "commercial_alignment" for case in data["cases"])
