"""Rongwei Automotive Sales Plugin.

The host AI performs semantic reasoning. This package prepares validated
business context and provides deterministic policy checks around its output.
"""
from .sales.analysis import build_sales_analysis_context, validate_analysis_result

__all__ = ["build_sales_analysis_context", "validate_analysis_result"]
__version__ = "0.1.0"
