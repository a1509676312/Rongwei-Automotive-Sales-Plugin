"""Model-agnostic MCP server exposing Rongwei sales capabilities.

Run with: python -m rongwei_plugin.mcp_server
Install optional dependency: pip install -e ".[mcp]"
The MCP host supplies the language model; this server does not call a provider.
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from rongwei_plugin.sales.analysis import (
    build_sales_analysis_context,
    validate_analysis_result,
)

mcp = FastMCP(
    "Rongwei Automotive Sales",
    instructions=(
        "You are using Rongwei's automotive-export sales capabilities. "
        "Use evidence-led reasoning, distinguish facts from inference and unknowns, "
        "never invent prices/specifications/stock/logistics/payment/delivery facts, "
        "and only draft replies. Never send messages."
    ),
)


@mcp.tool()
def prepare_sales_analysis(context: dict[str, Any]) -> dict[str, Any]:
    """Prepare a normalized automotive-export sales case and shared playbook.

    Input is user-provided context: conversation messages with buyer/seller speaker
    labels, optional advertisement/source data, vehicle candidates, buyer
    requirements, and prior follow-up context. Returns structured evidence and
    sales rules for the connected host model to reason over.
    """
    return build_sales_analysis_context(context)


@mcp.tool()
def validate_sales_analysis(result: dict[str, Any]) -> dict[str, Any]:
    """Validate critical Rongwei sales-analysis rules in a model-produced result.

    Checks buying stage, intent assessment, evidence labels, required next steps,
    and prohibited claims about close probability or automatic message sending.
    """
    return validate_analysis_result(result)


def main() -> None:
    """Start the MCP server over stdio for local AI-host integrations."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
