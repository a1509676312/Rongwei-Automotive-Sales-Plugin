from decimal import Decimal

import pytest
from pydantic import ValidationError

from rongwei_plugin.trade import QuoteInput, calculate_quote


def test_fob_quote_uses_only_fob_cost_scope():
    quote = QuoteInput(
        trade_term="FOB", quantity=2, currency="USD",
        vehicle_cost_per_unit=Decimal("10000"),
        inland_transport_total=Decimal("500"),
        export_handling_total=Decimal("300"),
        international_freight_total=Decimal("999"),
        insurance_total=Decimal("99"),
        profit_margin=Decimal("0.10"), origin_place="Shanghai",
        costs_confirmed=True,
    )
    result = calculate_quote(quote)
    assert result["included_cost_total"] == "20800.00"
    assert result["total_quote"] == "22880.00"
    assert result["unit_quote"] == "11440.00"


def test_cif_requires_confirmed_freight_and_insurance():
    with pytest.raises(ValidationError):
        QuoteInput(
            trade_term="CIF", quantity=1, currency="USD",
            vehicle_cost_per_unit=Decimal("10000"),
            insurance_total=Decimal("100"),
            profit_margin=Decimal("0.1"), named_destination="Hamburg",
        )


def test_cip_requires_named_destination_and_insurance():
    with pytest.raises(ValidationError):
        QuoteInput(
            trade_term="CIP", quantity=1, currency="USD",
            vehicle_cost_per_unit=Decimal("10000"),
            international_freight_total=Decimal("100"),
            insurance_total=Decimal("50"), freight_confirmed=True,
            insurance_confirmed=True, profit_margin=Decimal("0.1"),
        )
