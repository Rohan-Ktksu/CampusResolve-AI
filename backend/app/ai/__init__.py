"""Local NLTK-based assistance; no model, network, database, or ticket writes."""

from .issue_rules import find_common_issues
from .query_rules import describe_result, parse_query
from .report_rules import generate_admin_report
from .ticket_rules import analyze_complaint

__all__ = ["analyze_complaint", "describe_result", "find_common_issues", "generate_admin_report", "parse_query"]
