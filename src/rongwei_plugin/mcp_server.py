"""MCP server exposing Rongwei's sales tools to compatible AI hosts.

Run with `rw-mcp` after installing the optional `mcp` extra.
Transport is stdio so the host can launch it as a local child process.
"""
from __future__ import annotations

import json
from typing import Any

from rongwei_plugin.local_store import LocalStore
from rongwei_plugin.sales.playbook import get_objection_plan
from rongwei_plugin.sales.review import review_sales_execution
from rongwei_plugin.sales.scoring import assess_lead
from rongwei_plugin.models import LeadInput, ObjectionRequest, SalesExecutionInput
from rongwei_plugin.trade import QuoteInput, calculate_quote


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError('Install MCP support with: pip install -e ".[mcp]"') from exc

    server = FastMCP("Rongwei Automotive Export Sales Director")

    @server.tool()
    def rw_assess_automotive_export_lead(input_json: str) -> dict[str, Any]:
        """Analyze buyer intent, evidence, purchasing stage, blockers and next action."""
        data = LeadInput.model_validate_json(input_json)
        return assess_lead(data).model_dump(mode="json")

    @server.tool()
    def rw_get_objection_playbook(input_json: str) -> dict[str, Any]:
        """Build an evidence-safe strategy for a customer's primary objection."""
        data = ObjectionRequest.model_validate_json(input_json)
        return get_objection_plan(data).model_dump(mode="json")

    @server.tool()
    def rw_review_sales_execution(input_json: str) -> dict[str, Any]:
        """Review sales execution, missed answers, commitments and next steps."""
        data = SalesExecutionInput.model_validate_json(input_json)
        return review_sales_execution(data).model_dump(mode="json")

    @server.tool()
    def rw_create_customer(name: str = "", company: str = "", phone: str = "",
                           country: str = "", city: str = "", buyer_type: str = "unknown",
                           facts_json: str = "{}") -> dict[str, str]:
        """Create a customer record in this computer's local database."""
        facts = json.loads(facts_json or "{}")
        customer_id = LocalStore().create_customer(
            name=name or None, company=company or None, phone=phone or None,
            country=country or None, city=city or None, buyer_type=buyer_type,
            facts=facts,
        )
        return {"customer_id": customer_id, "storage": "local_only"}

    @server.tool()
    def rw_search_customers(query: str = "", country: str = "", limit: int = 30) -> dict[str, Any]:
        """Search only this user's local customer records."""
        return {"customers": LocalStore().search_customers(
            query=query or None, country=country or None, limit=limit
        )}

    @server.tool()
    def rw_get_customer(customer_id: str) -> dict[str, Any]:
        """Retrieve one local customer profile."""
        customer = LocalStore().get_customer(customer_id)
        return {"customer": customer} if customer else {"error": "customer_not_found"}

    @server.tool()
    def rw_append_customer_interaction(customer_id: str, content: str,
                                       source: str = "user_input",
                                       language: str = "") -> dict[str, str]:
        """Append a user-supplied chat excerpt or sales note to local customer history."""
        interaction_id = LocalStore().append_interaction(
            customer_id, content, source=source, language=language or None
        )
        return {"interaction_id": interaction_id, "saved": "true"}

    @server.tool()
    def rw_recommend_destination_ports(country: str, limit: int = 20) -> dict[str, Any]:
        """Recommend ports/terminals from same-country history with evidence status."""
        return {"country": country, "recommendations": LocalStore().recommend_ports(country, limit)}

    @server.tool()
    def rw_add_destination_port(country: str, name: str, city: str = "",
                                transport_type: str = "seaport",
                                status: str = "historical_reference",
                                source_customer_id: str = "",
                                source_note: str = "") -> dict[str, str]:
        """Save a port or inland logistics point and its confirmation status."""
        port_id = LocalStore().add_port(
            country, name, city=city or None, transport_type=transport_type,
            status=status, source_customer_id=source_customer_id or None,
            source_note=source_note or None,
        )
        return {"port_id": port_id, "status": status}

    @server.tool()
    def rw_calculate_export_quote(quote_json: str, customer_id: str = "") -> dict[str, Any]:
        """Calculate FOB/CIF/CIP from supplied costs; no missing cost or FX is invented."""
        quote = QuoteInput.model_validate_json(quote_json)
        result = calculate_quote(quote)
        quote_id = LocalStore().save_quote(
            payload=result, terms=quote.trade_term, currency=quote.currency,
            customer_id=customer_id or None,
        )
        return {"quote_id": quote_id, "quote": result}

    @server.tool()
    def rw_create_followup(customer_id: str, due_at: str, objective: str) -> dict[str, str]:
        """Save a due date and one concrete follow-up objective locally."""
        followup_id = LocalStore().add_followup(customer_id, due_at, objective)
        return {"followup_id": followup_id}

    @server.tool()
    def rw_get_due_followups(limit: int = 100) -> dict[str, Any]:
        """List overdue and due follow-up tasks from the local database."""
        return {"followups": LocalStore().list_due_followups(limit=limit)}

    @server.tool()
    def rw_save_sales_experience(context: str, outcome: str, confidence: str,
                                 country: str = "", buyer_type: str = "",
                                 selected_strategy: str = "",
                                 source_customer_id: str = "") -> dict[str, str]:
        """Save a learning record with explicit evidence confidence."""
        experience_id = LocalStore().add_experience(
            context=context, outcome=outcome, confidence=confidence,
            country=country or None, buyer_type=buyer_type or None,
            selected_strategy=selected_strategy or None,
            source_customer_id=source_customer_id or None,
        )
        return {"experience_id": experience_id, "confidence": confidence}

    @server.tool()
    def rw_find_sales_experiences(country: str = "", buyer_type: str = "",
                                  limit: int = 20) -> dict[str, Any]:
        """Retrieve prior local sales experience; results are references, not customer facts."""
        return {"experiences": LocalStore().find_experiences(
            country=country or None, buyer_type=buyer_type or None, limit=limit
        )}

    @server.tool()
    def rw_backup_local_data() -> dict[str, str]:
        """Create a verified local SQLite backup."""
        return {"backup_file": str(LocalStore().backup()), "status": "ok"}

    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
