from fastapi.testclient import TestClient

from rongwei_plugin.api.app import app

client = TestClient(app)


def test_health_is_public_and_contains_no_sensitive_data():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tool_catalog_requires_configured_api_key(monkeypatch):
    monkeypatch.delenv("RONGWEI_API_KEY", raising=False)
    response = client.get("/v1/tools")
    assert response.status_code == 503

    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    denied = client.get("/v1/tools")
    assert denied.status_code == 401
    allowed = client.get("/v1/tools", headers={"X-Rongwei-API-Key": "test-secret"})
    assert allowed.status_code == 200
    assert len(allowed.json()["tools"]) == 3


def test_tool_endpoint_executes_validated_business_logic(monkeypatch):
    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    response = client.post(
        "/v1/tools/rw_get_objection_playbook",
        headers={"X-Rongwei-API-Key": "test-secret"},
        json={"objection": "shipping_and_port"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["result"]["suggested_question"]


def test_validation_error_does_not_echo_private_input(monkeypatch):
    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    private_value = "private customer phone 555-0100"
    response = client.post(
        "/v1/tools/rw_assess_automotive_export_lead",
        headers={"X-Rongwei-API-Key": "test-secret"},
        json={"facts": {"vehicle_model": private_value}},
    )
    assert response.status_code == 422
    assert private_value not in response.text


def test_tool_dispatch_http_endpoint_preserves_call_id(monkeypatch):
    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    response = client.post(
        "/v1/tool-calls/dispatch",
        headers={"X-Rongwei-API-Key": "test-secret"},
        json={
            "tool_calls": [
                {
                    "id": "call-http",
                    "function": {
                        "name": "rw_get_objection_playbook",
                        "arguments": '{"objection":"price_or_total_cost"}',
                    },
                }
            ]
        },
    )
    assert response.status_code == 200
    tool_message = response.json()["tool_messages"][0]
    assert tool_message["tool_call_id"] == "call-http"
    assert tool_message["role"] == "tool"



def test_openapi_exposes_typed_business_endpoints():
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/v1/sales/assess-lead" in paths
    assert "/v1/sales/objection-playbook" in paths
    assert "/v1/sales/review-execution" in paths
    body_schema = paths["/v1/sales/assess-lead"]["post"]["requestBody"]
    assert body_schema["content"]["application/json"]["schema"]


def test_typed_lead_endpoint_requires_fact_evidence(monkeypatch):
    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    phone_like = "555-0100"
    response = client.post(
        "/v1/sales/assess-lead",
        headers={"X-Rongwei-API-Key": "test-secret"},
        json={"facts": {"vehicle_model": phone_like}},
    )
    assert response.status_code == 422
    assert phone_like not in response.text


def test_typed_objection_endpoint_returns_stage_context(monkeypatch):
    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    response = client.post(
        "/v1/sales/objection-playbook",
        headers={"X-Rongwei-API-Key": "test-secret"},
        json={
            "objection": "payment_security",
            "current_stage": "order_process",
            "confirmed_facts": ["已核对公司主体"],
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert "订单流程" in result["case_specific_note"]
    assert "已核对公司主体" in result["case_specific_note"]


def test_typed_sales_review_endpoint_distinguishes_unknown_from_false(monkeypatch):
    monkeypatch.setenv("RONGWEI_API_KEY", "test-secret")
    response = client.post(
        "/v1/sales/review-execution",
        headers={"X-Rongwei-API-Key": "test-secret"},
        json={},
    )
    assert response.status_code == 200
    assert response.json()["rating"] == "acceptable"
    assert response.json()["missed_opportunities"] == []
