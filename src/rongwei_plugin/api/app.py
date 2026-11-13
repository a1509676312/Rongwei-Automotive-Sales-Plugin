"""FastAPI transport for Rongwei's canonical sales tools.

Set RONGWEI_API_KEY before using the HTTP endpoints. The health endpoint is public;
tool listing and execution endpoints require the configured key.
"""
from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException
from pydantic import ValidationError

from rongwei_plugin import __version__
from rongwei_plugin.tool_dispatch import ToolCallDispatchError, execute_provider_tool_calls
from rongwei_plugin.tools.catalog import execute_tool, get_tool_catalog, registered_tool_names

app = FastAPI(
    title="Rongwei Automotive Sales Plugin",
    version=__version__,
    description=(
        "Evidence-led automotive export sales tools. Tool calls generate analysis and "
        "draft guidance only; this API does not connect to messaging channels or send messages."
    ),
)


def _require_api_key(x_rongwei_api_key: str | None) -> None:
    expected = os.getenv("RONGWEI_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="HTTP tools are disabled until RONGWEI_API_KEY is configured.",
        )
    if not x_rongwei_api_key or not secrets.compare_digest(x_rongwei_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Basic liveness endpoint; contains no customer or credential data."""
    return {"status": "ok", "version": __version__}


@app.get("/v1/tools", tags=["tools"])
def list_tools(
    x_rongwei_api_key: str | None = Header(default=None, alias="X-Rongwei-API-Key"),
) -> dict[str, Any]:
    """List canonical tool definitions for a host AI platform."""
    _require_api_key(x_rongwei_api_key)
    return {"tools": get_tool_catalog()}


@app.post("/v1/tools/{tool_name}", tags=["tools"])
def call_tool(
    tool_name: str,
    payload: dict[str, Any] = Body(...),
    x_rongwei_api_key: str | None = Header(default=None, alias="X-Rongwei-API-Key"),
) -> dict[str, Any]:
    """Execute one canonical tool call."""
    _require_api_key(x_rongwei_api_key)
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


@app.post("/v1/tool-calls/dispatch", tags=["tools"])
def dispatch_tool_calls(
    payload: dict[str, Any] = Body(...),
    x_rongwei_api_key: str | None = Header(default=None, alias="X-Rongwei-API-Key"),
) -> dict[str, Any]:
    """Execute one bounded provider tool-call batch and return role=tool messages."""
    _require_api_key(x_rongwei_api_key)
    calls = payload.get("tool_calls")
    if not isinstance(calls, list):
        raise HTTPException(status_code=422, detail="tool_calls must be a JSON array.")
    try:
        return {"tool_messages": execute_provider_tool_calls(calls)}
    except ToolCallDispatchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
