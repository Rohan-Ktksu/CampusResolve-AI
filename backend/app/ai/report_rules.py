"""Evidence-backed local summaries of backend-calculated report aggregates."""

import math
from collections import Counter
from collections.abc import Mapping
from datetime import date, datetime

from .ticket_rules import action_for_category


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError("Report counts must be nonnegative integers.")
    return value


def generate_admin_report(aggregates):
    """Return AdminReport using only the supplied, authorized aggregate evidence.

    The frozen Insights input has no category-to-department map, so department_id
    remains null; the administrator chooses a responsible team in the existing UI.
    """
    if not isinstance(aggregates, Mapping):
        raise ValueError("Report aggregates must be a mapping.")
    period = aggregates["period"]
    start, end = date.fromisoformat(period["from"]), date.fromisoformat(period["to"])
    if not 0 <= (end - start).days < 366:
        raise ValueError("Report period is invalid or exceeds 366 days.")
    generated_at = aggregates["generated_at"]
    if datetime.fromisoformat(generated_at.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Report timestamp must include its timezone.")
    sample = _count(aggregates["sample_size"])
    unresolved = _count(aggregates["unresolved"])
    urgent = _count(aggregates["high_priority_unresolved"])
    resolved = _count(aggregates["resolved_count"])
    if urgent > unresolved or unresolved + resolved > sample:
        raise ValueError("Report counts are inconsistent.")
    average = aggregates["avg_resolution_hours"]
    if average is not None and (type(average) not in (int, float) or not math.isfinite(average) or average < 0):
        raise ValueError("Resolution average must be a finite nonnegative number or null.")
    if (resolved == 0) != (average is None):
        raise ValueError("Resolution average must be null exactly when no resolved tickets exist.")

    categories = aggregates["by_category"]
    locations = aggregates["by_location"]
    if not isinstance(categories, list) or not isinstance(locations, list):
        raise ValueError("Category/location aggregates must be lists.")
    if sum(_count(row["count"]) for row in categories) != sample or sum(_count(row["count"]) for row in locations) != sample:
        raise ValueError("Category and location counts must each match the report sample.")
    for row in categories:
        if not isinstance(row["category"], str) or not row["category"].strip():
            raise ValueError("Category labels are required.")
    for row in locations:
        if not isinstance(row["location"], str) or not row["location"].strip():
            raise ValueError("Location labels are required.")

    result = {
        "period": {"from": period["from"], "to": period["to"]},
        "sample_size": sample,
        "generated_at": generated_at,
        "source": "rules",
        "summary": "No complaints were reported in this period; there is insufficient evidence to recommend improvements.",
        "recommendations": [],
    }
    if sample == 0:
        return result

    top = sorted(categories, key=lambda row: (-row["count"], row["category"]))[0]
    location_counts = Counter()
    for row in locations:
        location_counts[row["location"]] += row["count"]
    hotspot, hotspot_count = sorted(location_counts.items(), key=lambda item: (-item[1], item[0]))[0]
    summary = (f"{sample} reported tickets in the selected creation-date cohort; {unresolved} currently unresolved, "
               f"including {urgent} high-priority reports. {top['category']} accounts for {top['count']} of {sample} tickets. "
               f"{hotspot} has {hotspot_count} reported tickets. Counts measure reports, not unique affected people.")
    if average is not None:
        summary += f" Mean resolution time is {average:.2f} hours across {resolved} resolved tickets."
    else:
        summary += " No resolved tickets are available for a resolution-time average."
    result["summary"] = summary

    recs = result["recommendations"]
    if urgent:
        recs.append({
            "title": "Review high-priority unresolved issues first",
            "evidence": f"{urgent} of {unresolved} unresolved reports are currently marked HIGH.",
            "department_id": None,
            "next_step": "Have the coordinator verify urgency, assign qualified staff, and track action separately from complaint frequency.",
            "horizon": "IMMEDIATE",
        })
    recs.append({
        "title": f"Assess recurring {top['category']} complaints",
        "evidence": f"{top['count']} of {sample} reported tickets ({100 * top['count'] / sample:.1f}%) concern {top['category']}.",
        "department_id": None,
        "next_step": action_for_category(top["category"]),
        "horizon": "ASSESSMENT",
    })
    recs.append({
        "title": f"Inspect reported issues at {hotspot}",
        "evidence": f"{hotspot_count} of {sample} reported tickets are located at {hotspot}, across the supplied category groups.",
        "department_id": None,
        "next_step": "Review the location's tickets with the responsible departments and inspect conditions before proposing repairs or development spending.",
        "horizon": "ASSESSMENT",
    })
    if unresolved and not urgent:
        recs.append({
            "title": "Review the unresolved queue",
            "evidence": f"{unresolved} of {sample} reported tickets remain unresolved.",
            "department_id": None,
            "next_step": "Check queue age and ownership, verify priorities, and agree the next action with assigned departments.",
            "horizon": "IMMEDIATE",
        })
    return result
