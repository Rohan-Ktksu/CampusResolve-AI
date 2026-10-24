"""Evidence-backed local summaries of backend-calculated report aggregates."""

import math
from collections import Counter
from collections.abc import Mapping
from datetime import date, datetime

from .nlp import key_terms
from .ticket_rules import action_for_category


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError("Report counts must be nonnegative integers.")
    return value


def _plural(count, word):
    return word if count == 1 else word + "s"


def generate_admin_report(aggregates, texts=()):
    """Return AdminReport using only the supplied, authorized aggregate evidence.

    `texts` are the cohort's complaint titles/descriptions. When given, NLTK key terms are
    added and source becomes "nlp". Complaint text itself is never quoted (AI_CONTRACT).

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
    if not isinstance(texts, (list, tuple)) or len(texts) > sample or not all(isinstance(t, str) for t in texts):
        raise ValueError("Complaint texts must be a list of strings from the report sample.")
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

    categorized = [row for row in categories if row.get("category_id") is not None
                   and row["category"].strip().casefold() != "uncategorized" and row["count"] > 0]
    top = sorted(categorized, key=lambda row: (-row["count"], row["category"]))[0] if categorized else None
    unclassified = sample - sum(row["count"] for row in categorized)
    location_counts = Counter()
    for row in locations:
        location_counts[row["location"]] += row["count"]
    hotspot, hotspot_count = sorted(location_counts.items(), key=lambda item: (-item[1], item[0]))[0]
    summary = (f"{sample} reported {_plural(sample, 'ticket')} in the selected creation-date cohort; {unresolved} currently unresolved, "
               f"including {urgent} high-priority {_plural(urgent, 'report')}. ")
    if top:
        summary += f"Among categorized issues, {top['category']} accounts for {top['count']} of {sample} {_plural(sample, 'ticket')}. "
    if unclassified:
        summary += f"{unclassified} {_plural(unclassified, 'ticket')} still {'needs' if unclassified == 1 else 'need'} category review. "
    summary += (f"{hotspot} has {hotspot_count} reported {_plural(hotspot_count, 'ticket')}. "
                "Counts measure reports, not unique affected people.")
    if average is not None:
        summary += f" Mean resolution time is {average:.2f} hours across {resolved} resolved {_plural(resolved, 'ticket')}."
    else:
        summary += " No resolved tickets are available for a resolution-time average."
    terms = key_terms(texts) if texts else []
    if texts:
        result["source"] = "nlp"
        if terms:
            summary += " Most-mentioned terms: " + ", ".join(f"{word} ({n})" for word, n in terms) + "."
    result["summary"] = summary

    recs = result["recommendations"]
    if urgent:
        recs.append({
            "title": "Review high-priority unresolved issues first",
            "evidence": f"{urgent} of {unresolved} unresolved {_plural(unresolved, 'report')} {'is' if urgent == 1 else 'are'} currently marked HIGH.",
            "department_id": None,
            "next_step": "Have the coordinator verify urgency, assign qualified staff, and track action separately from complaint frequency.",
            "horizon": "IMMEDIATE",
        })
    if top:
        recs.append({
            "title": f"Assess recurring {top['category']} complaints" if top['count'] > 1 else f"Review the {top['category']} report",
            "evidence": f"{top['count']} of {sample} reported {_plural(sample, 'ticket')} ({100 * top['count'] / sample:.1f}%) {'concerns' if top['count'] == 1 else 'concern'} {top['category']}.",
            "department_id": None,
            "next_step": action_for_category(top["category"]),
            "horizon": "ASSESSMENT",
        })
    else:
        recs.append({
            "title": "Categorize unclassified reports",
            "evidence": f"{unclassified} of {sample} reported {_plural(sample, 'ticket')} {'has' if unclassified == 1 else 'have'} no usable category.",
            "department_id": None,
            "next_step": "Review these reports and assign suitable configured categories before inferring recurring service problems or development priorities.",
            "horizon": "ASSESSMENT",
        })
    if terms and terms[0][1] >= 3:
        word, n = terms[0]
        recs.append({
            "title": f"Look into recurring mentions of '{word}'",
            "evidence": f"'{word}' appears in {n} of {sample} reported {_plural(sample, 'ticket')} (NLTK term frequency).",
            "department_id": None,
            "next_step": f"Read the tickets mentioning '{word}' together to confirm whether they describe one underlying problem before acting.",
            "horizon": "ASSESSMENT",
        })
    recs.append({
        "title": f"Inspect reported issues at {hotspot}",
        "evidence": f"{hotspot_count} of {sample} reported {_plural(sample, 'ticket')} {'is' if hotspot_count == 1 else 'are'} located at {hotspot}, across the supplied category groups.",
        "department_id": None,
        "next_step": "Review the location's tickets with the responsible departments and inspect conditions before proposing repairs or development spending.",
        "horizon": "ASSESSMENT",
    })
    if unresolved and not urgent:
        recs.append({
            "title": "Review the unresolved queue",
            "evidence": f"{unresolved} of {sample} reported {_plural(sample, 'ticket')} {'remains' if unresolved == 1 else 'remain'} unresolved.",
            "department_id": None,
            "next_step": "Check queue age and ownership, verify priorities, and agree the next action with assigned departments.",
            "horizon": "IMMEDIATE",
        })
    return result
