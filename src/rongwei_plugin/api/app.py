"""FastAPI transport for Rongwei's canonical sales tools.

Set RONGWEI_API_KEY before using HTTP tool endpoints. The health endpoint is public;
all tool listing and execution endpoints require the configured key.
"""
from __future__ import annotations

import os
import secrets
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from rongwei_plugin import __version__
from rongwei_plugin.models import (
    LeadAssessment,
    LeadInput,
    ObjectionPlan,
    ObjectionRequest,
    SalesExecutionInput,
    SalesExecutionReview,
)
from rongwei_plugin.sales.playbook import get_objection_plan
from rongwei_plugin.sales.review import review_sales_execution
from rongwei_plugin.sales.scoring import assess_lead
from rongwei_plugin.tool_dispatch import ToolCallDispatchError, execute_provider_tool_calls
from rongwei_plugin.local_store import LocalStore
from rongwei_plugin.trade import QuoteInput, calculate_quote
from rongwei_plugin.tools.catalog import execute_tool, get_tool_catalog, registered_tool_names

app = FastAPI(
    title="Rongwei Automotive Sales Plugin",
    version=__version__,
    description=(
        "Evidence-led automotive export sales tools. Tool calls generate analysis and "
        "draft guidance only; this API does not connect to messaging channels or send messages."
    ),
)


def _require_api_key(
    x_rongwei_api_key: str | None = Header(default=None, alias="X-Rongwei-API-Key"),
) -> None:
    expected = os.getenv("RONGWEI_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="HTTP tools are disabled until RONGWEI_API_KEY is configured.",
        )
    if not x_rongwei_api_key or not secrets.compare_digest(x_rongwei_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Avoid echoing user-provided values such as phone numbers in 422 responses."""
    issues = [
        {
            "location": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", "Invalid value."),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": {"error": "invalid_arguments", "issues": issues}},
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Basic liveness endpoint; contains no customer or credential data."""
    return {"status": "ok", "version": __version__}


@app.get("/v1/tools", tags=["tools"], dependencies=[Depends(_require_api_key)])
def list_tools() -> dict[str, Any]:
    """List canonical tool definitions for function-calling host applications."""
    return {"tools": get_tool_catalog()}


@app.post(
    "/v1/sales/assess-lead",
    tags=["sales"],
    response_model=LeadAssessment,
    dependencies=[Depends(_require_api_key)],
)
def assess_lead_endpoint(payload: LeadInput) -> LeadAssessment:
    """Analyze a buyer's evidence, purchase stage, blockers, and next sales action."""
    return assess_lead(payload)


@app.post(
    "/v1/sales/objection-playbook",
    tags=["sales"],
    response_model=ObjectionPlan,
    dependencies=[Depends(_require_api_key)],
)
def objection_playbook_endpoint(payload: ObjectionRequest) -> ObjectionPlan:
    """Create a stage-aware strategy for one primary buyer objection."""
    return get_objection_plan(payload)


@app.post(
    "/v1/sales/review-execution",
    tags=["sales"],
    response_model=SalesExecutionReview,
    dependencies=[Depends(_require_api_key)],
)
def review_execution_endpoint(payload: SalesExecutionInput) -> SalesExecutionReview:
    """Review the seller's observable actions and highlight missed opportunities."""
    return review_sales_execution(payload)


@app.post(
    "/v1/tools/{tool_name}",
    tags=["tools"],
    dependencies=[Depends(_require_api_key)],
)
def call_tool(
    tool_name: str,
    payload: Annotated[dict[str, Any], Body()],
) -> dict[str, Any]:
    """Dynamically execute one canonical tool call."""
    if tool_name not in registered_tool_names():
        raise HTTPException(status_code=404, detail="Unknown Rongwei tool.")
    try:
        return {"ok": True, "result": execute_tool(tool_name, payload)}
    except ValidationError as exc:
        issues = [
            {
                "location": ".".join(str(part) for part in error.get("loc", ())),
                "message": error.get("msg", "Invalid value."),
                "type": error.get("type", "validation_error"),
            }
            for error in exc.errors(include_input=False)
        ]
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_arguments", "issues": issues},
        ) from exc


@app.post(
    "/v1/tool-calls/dispatch",
    tags=["tools"],
    dependencies=[Depends(_require_api_key)],
)
def dispatch_tool_calls(payload: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
    """Execute one bounded provider tool-call batch and return role=tool messages."""
    calls = payload.get("tool_calls")
    if not isinstance(calls, list):
        raise HTTPException(status_code=422, detail="tool_calls must be a JSON array.")
    try:
        return {"tool_messages": execute_provider_tool_calls(calls)}
    except ToolCallDispatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



# Local-first customer memory and sales operations. These routes write only to the
# per-user data directory and remain protected by the local API key.
@app.post("/v1/local/customers", tags=["local-memory"], dependencies=[Depends(_require_api_key)])
def create_local_customer(payload: dict[str, Any]) -> dict[str, str]:
    store = LocalStore()
    customer_id = store.create_customer(
        name=payload.get("name"), company=payload.get("company"),
        phone=payload.get("phone"), country=payload.get("country"),
        city=payload.get("city"), buyer_type=payload.get("buyer_type"),
        facts=payload.get("facts") or {}, whatsapp=payload.get("whatsapp"),
        telegram=payload.get("telegram"), email=payload.get("email"),
    )
    return {"customer_id": customer_id}


@app.get("/v1/local/customers", tags=["local-memory"], dependencies=[Depends(_require_api_key)])
def search_local_customers(country: str | None = None, query: str | None = None,
                           limit: int = 50) -> dict[str, Any]:
    return {"customers": LocalStore().search_customers(country=country, query=query, limit=limit)}


@app.get("/v1/local/customers/{customer_id}", tags=["local-memory"], dependencies=[Depends(_require_api_key)])
def get_local_customer(customer_id: str) -> dict[str, Any]:
    customer = LocalStore().get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return customer


@app.post("/v1/local/customers/{customer_id}/interactions", tags=["local-memory"],
          dependencies=[Depends(_require_api_key)])
def append_local_interaction(customer_id: str, payload: dict[str, Any]) -> dict[str, str]:
    interaction_id = LocalStore().append_interaction(
        customer_id, str(payload.get("content", "")),
        source=str(payload.get("source", "user_input")),
        language=payload.get("language"), occurred_at=payload.get("occurred_at"),
        evidence=payload.get("evidence") or {},
    )
    return {"interaction_id": interaction_id}


@app.get("/v1/local/customers/{customer_id}/interactions", tags=["local-memory"],
         dependencies=[Depends(_require_api_key)])
def get_local_interactions(customer_id: str, limit: int = 100) -> dict[str, Any]:
    return {"interactions": LocalStore().list_interactions(customer_id, limit=limit)}


@app.post("/v1/local/ports", tags=["port-knowledge"], dependencies=[Depends(_require_api_key)])
def add_local_port(payload: dict[str, Any]) -> dict[str, str]:
    port_id = LocalStore().add_port(
        country=payload["country"], name=payload["name"], city=payload.get("city"),
        transport_type=payload.get("transport_type", "seaport"),
        status=payload.get("status", "historical_reference"),
        source_customer_id=payload.get("source_customer_id"),
        source_note=payload.get("source_note"), confirmed_at=payload.get("confirmed_at"),
    )
    return {"port_id": port_id}


@app.get("/v1/local/ports/{country}", tags=["port-knowledge"],
         dependencies=[Depends(_require_api_key)])
def recommend_local_ports(country: str, limit: int = 20) -> dict[str, Any]:
    return {"country": country, "recommendations": LocalStore().recommend_ports(country, limit)}


@app.post("/v1/local/customers/{customer_id}/followups", tags=["follow-up"],
          dependencies=[Depends(_require_api_key)])
def add_local_followup(customer_id: str, payload: dict[str, Any]) -> dict[str, str]:
    followup_id = LocalStore().add_followup(customer_id, payload["due_at"], payload["objective"])
    return {"followup_id": followup_id}


@app.get("/v1/local/followups/due", tags=["follow-up"], dependencies=[Depends(_require_api_key)])
def get_due_local_followups(limit: int = 100) -> dict[str, Any]:
    return {"followups": LocalStore().list_due_followups(limit=limit)}


@app.post("/v1/local/quotes", tags=["quote"], dependencies=[Depends(_require_api_key)])
def calculate_and_save_local_quote(payload: dict[str, Any]) -> dict[str, Any]:
    quote_payload = payload.get("quote")
    if quote_payload is None:
        quote_payload = {key: value for key, value in payload.items() if key != "customer_id"}
    quote_data = QuoteInput.model_validate(quote_payload)
    result = calculate_quote(quote_data)
    customer_id = payload.get("customer_id")
    quote_id = LocalStore().save_quote(
        payload=result, terms=quote_data.trade_term, currency=quote_data.currency,
        customer_id=customer_id,
    )
    return {"quote_id": quote_id, "quote": result}


@app.get("/v1/local/customers/{customer_id}/quotes", tags=["quote"],
         dependencies=[Depends(_require_api_key)])
def get_local_quote_history(customer_id: str, limit: int = 50) -> dict[str, Any]:
    return {"quotes": LocalStore().list_quotes(customer_id, limit=limit)}


@app.post("/v1/local/backup", tags=["local-memory"], dependencies=[Depends(_require_api_key)])
def backup_local_data() -> dict[str, str]:
    path = LocalStore().backup()
    return {"status": "ok", "backup_file": str(path)}
