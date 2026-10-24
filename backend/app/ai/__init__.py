"""Local rules-based assistance; no model, network, database, or ticket writes."""

from .report_rules import generate_admin_report
from .ticket_rules import analyze_complaint

__all__ = ["analyze_complaint", "generate_admin_report"]
