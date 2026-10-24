"""Admin chatbox: English question -> allow-listed query plan, and plan results -> summary + suggestions.

The parser never produces SQL. It only fills a fixed plan that the backend validates and runs
with parameterized queries. NLTK stemming lets "leaking taps in hostel 1 last month" map to
configured categories, locations and dates.
"""

import calendar
import re
from datetime import date, timedelta

from .nlp import content_stems, has_phrase, key_terms, normalize, stem, tokens
from .ticket_rules import RULES, _family, action_for_category

DEFAULT_DAYS = 30
MAX_DAYS = 366
OPEN = ["SUBMITTED", "IN_PROGRESS"]
MONTHS = {name.casefold(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.casefold(): i for i, name in enumerate(calendar.month_abbr) if name})
MONTHS["sept"] = 9
PREPOSITIONS = {"in", "at", "near", "from", "inside", "around", "outside"}
GROUPS = {
    "category": r"categor(?:y|ies)|types?|kinds?|issues?|problems?",
    "location": r"locations?|places?|buildings?|blocks?|areas?",
    "department": r"departments?|depts?|teams?",
    "status": r"status(?:es)?",
    "priority": r"priorit(?:y|ies)",
    "day": r"days?",
    "week": r"weeks?",
    "month": r"months?",
}
TIME_GROUPS = ("day", "week", "month")


def _has(text, pattern):
    return re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)", text) is not None


def _period(raw, today, warnings):
    """Return (from, to) for the first date expression found, else the default window."""
    iso = r"(\d{4}-\d{2}-\d{2})"
    m = re.search(iso + r"\s*(?:to|until|till|and|through|-)\s*" + iso, raw)
    if m:
        return date.fromisoformat(m[1]), date.fromisoformat(m[2])
    m = re.search(r"(?:since|from|after)\s+" + iso, raw)
    if m:
        return date.fromisoformat(m[1]), today
    m = re.search(r"\bon\s+" + iso, raw)
    if m:
        d = date.fromisoformat(m[1])
        return d, d
    if _has(raw, "today"):
        return today, today
    if _has(raw, "yesterday"):
        return today - timedelta(days=1), today - timedelta(days=1)
    m = re.search(r"(?:last|past|previous)\s+(\d{1,3})\s+(day|week|month)s?", raw)
    if m:
        days = int(m[1]) * {"day": 1, "week": 7, "month": 30}[m[2]]
        return today - timedelta(days=days - 1), today
    week_start = today - timedelta(days=today.weekday())
    if _has(raw, r"this\s+week"):
        return week_start, today
    if _has(raw, r"(?:last|previous)\s+week"):
        return week_start - timedelta(days=7), week_start - timedelta(days=1)
    month_start = today.replace(day=1)
    if _has(raw, r"this\s+month"):
        return month_start, today
    if _has(raw, r"(?:last|previous)\s+month"):
        end = month_start - timedelta(days=1)
        return end.replace(day=1), end
    if _has(raw, r"this\s+year"):
        return today.replace(month=1, day=1), today
    m = re.search(r"\b(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\b(?:\s+(\d{4}))?", raw)
    if m and not (m[1] == "may" and not m[2]):  # bare "may" is usually the verb
        month = MONTHS[m[1]]
        year = int(m[2]) if m[2] else today.year - (month > today.month)
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    warnings.append(f"No date range found; using the last {DEFAULT_DAYS} days.")
    return today - timedelta(days=DEFAULT_DAYS - 1), today


def _segments(name):
    return [s for s in re.split(r"[/,]", name) if s.strip()]


def _find(seq, sub):
    for i in range(len(seq) - len(sub) + 1):
        if seq[i:i + len(sub)] == sub:
            return i
    return -1


def parse_query(text, categories, departments, locations, today=None):
    """Return {"plan": QueryPlan dict, "warnings": [str]} for an admin's English question.

    categories/departments: [{"id", "name"}] active configuration; locations: [str].
    """
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise ValueError("Question must be 1-500 characters.")
    today = today or date.today()
    warnings = []
    raw = " ".join(text.casefold().split())
    start, end = _period(raw, today, warnings)
    if start > end:
        start, end = end, start
    if (end - start).days + 1 > MAX_DAYS:
        start = end - timedelta(days=MAX_DAYS - 1)
        warnings.append(f"Date range limited to {MAX_DAYS} days.")

    text_n = normalize(re.sub(r"\d{4}-\d{2}-\d{2}", " ", text))

    # Departments only count when named as a team ("IT department", "assigned to Facilities"),
    # because names like Facilities or Transport are also category words.
    department_ids = []
    for row in departments:
        name = re.escape(normalize(row["name"]))
        pattern = rf"(?:{name}\s+(?:department|dept|team|staff)|(?:assigned to|handled by|department of)\s+(?:the\s+)?{name})"
        if _has(text_n, pattern):
            department_ids.append(row["id"])
            text_n = re.sub(r"(?<!\w)" + pattern + r"(?!\w)", " ", text_n)

    # Locations: match any "/"-separated part of the name ("Hostel 1", "Lab 204").
    label_stems = {stem(w) for labels, _, _ in RULES.values() for label in labels for w in tokens(label)}
    label_stems |= {s for row in categories for s in content_stems(row["name"])}
    words = tokens(text_n)
    word_stems = [stem(w) for w in words]
    matched_locations = []
    for name in locations:
        for segment in _segments(name):
            seg = [stem(w) for w in tokens(segment)]
            i = _find(word_stems, seg) if seg else -1
            if i < 0:
                continue
            # "library complaints" is the Library category; "complaints in the library" is the place.
            ambiguous = all(s in label_stems for s in seg)
            before = {w for w in words[max(0, i - 2):i]}
            if ambiguous and not before & PREPOSITIONS:
                continue
            matched_locations.append(name)
            words[i:i + len(seg)] = ["_"] * len(seg)
            word_stems[i:i + len(seg)] = ["_"] * len(seg)
            break
    remaining = " ".join(w for w in words if w != "_")
    stems = content_stems(remaining)

    category_ids = []
    for row in categories:
        family = _family(row["name"])
        phrases = [row["name"], *(RULES[family][0] + RULES[family][1] if family else ())]
        if any(has_phrase(stems, p) for p in phrases):
            category_ids.append(row["id"])

    statuses = []
    if _has(remaining, r"unresolved|open|pending|outstanding|backlog|unsolved|not resolved|not closed|not fixed"):
        statuses = list(OPEN)
    else:
        if _has(remaining, r"in progress|ongoing|being worked on"):
            statuses.append("IN_PROGRESS")
        if _has(remaining, r"new|submitted|not started"):
            statuses.append("SUBMITTED")
        if _has(remaining, r"resolved|closed|fixed|solved|completed|done"):
            statuses.append("RESOLVED")
        if _has(remaining, r"rejected|declined|dismissed"):
            statuses.append("REJECTED")

    priorities = []
    if _has(remaining, r"high|urgent|critical|severe|emergency|serious"):
        priorities.append("HIGH")
    if _has(remaining, r"low priority|minor|low"):
        priorities.append("LOW")
    if _has(remaining, r"normal priority"):
        priorities.append("NORMAL")

    group_by = None
    for key, pattern in GROUPS.items():
        if _has(remaining, rf"(?:by|per|each|every|across|which|what|top(?:\s+\d{{1,3}})?)\s+(?:the\s+)?(?:{pattern})|(?:{pattern})\s*wise"):
            group_by = key
            break
    if group_by is None:
        if _has(remaining, r"daily"):
            group_by = "day"
        elif _has(remaining, r"weekly|trend|over time"):
            group_by = "week"
        elif _has(remaining, r"monthly"):
            group_by = "month"
        elif _has(remaining, r"where"):
            group_by = "location"
        elif _has(remaining, r"most common|most frequent|most reported|top|worst|biggest"):
            group_by = "category"

    limit = 50
    m = re.search(r"\btop\s+(\d{1,3})\b", remaining)
    if m:
        limit = max(1, min(200, int(m[1])))
    elif group_by and _has(remaining, r"top|most common|most frequent|most reported|worst|biggest"):
        limit = 5

    if _has(remaining, r"average|avg|mean|how long|resolution time|time to resolve|turnaround|slowest|fastest"):
        metric = "avg_resolution"
    elif group_by is None and _has(remaining, r"list|show|which tickets?|which complaints?|oldest|newest|latest|recent|details"):
        metric = "list"
    else:
        metric = "count"

    plan = {
        "metric": metric, "group_by": group_by, "category_ids": category_ids, "department_ids": department_ids,
        "locations": matched_locations, "statuses": statuses, "priorities": priorities,
        "from": start.isoformat(), "to": end.isoformat(), "limit": limit,
        "oldest_first": metric == "list" and _has(remaining, r"oldest|longest|earliest"),
    }
    if not (category_ids or department_ids or matched_locations or statuses or priorities or group_by or metric != "count"):
        warnings.append("No category, location, department, status or grouping recognised; showing overall totals.")
    return {"plan": plan, "warnings": warnings}


def _plural(n, word):
    return word if n == 1 else word + "s"


def describe_result(plan, totals, rows, texts, filter_labels):
    """Return (summary, suggestions) restating only the computed numbers and ticket text terms.

    totals: {"tickets", "unresolved", "resolved", "high_open", "avg_resolution_hours"}
    rows: result table rows (grouped rows have label/tickets/unresolved/resolved/avg_resolution_hours).
    """
    total, open_, resolved = totals["tickets"], totals["unresolved"], totals["resolved"]
    avg = totals["avg_resolution_hours"]
    scope = f" ({', '.join(filter_labels)})" if filter_labels else ""
    summary = (f"{total} {_plural(total, 'ticket')}{scope} from {plan['from']} to {plan['to']}: "
               f"{open_} unresolved, {resolved} resolved")
    summary += f", average resolution {avg:.1f} hours." if avg is not None else "."
    group = plan["group_by"]
    suggestions = []
    if total == 0:
        return summary, [{"title": "No matching tickets",
                          "evidence": f"0 tickets matched from {plan['from']} to {plan['to']}.",
                          "next_step": "Widen the date range or remove a filter chip and ask again."}]

    if plan["metric"] == "list":
        summary += f" Showing {len(rows)}, {'oldest' if plan['oldest_first'] else 'newest'} first."
    elif group in TIME_GROUPS:
        summary += f" Split into {len(rows)} {_plural(len(rows), group)}."
    elif group and rows:
        if plan["metric"] == "avg_resolution":
            timed = [r for r in rows if r["avg_resolution_hours"] is not None]
            if timed:
                summary += f" Slowest {group}: {timed[0]['label']} ({timed[0]['avg_resolution_hours']:.1f} hours)."
        else:
            summary += f" Top {group}: {rows[0]['label']} with {rows[0]['tickets']} {_plural(rows[0]['tickets'], 'ticket')}."
    terms = key_terms(texts, limit=3)
    if terms:
        summary += " Most-mentioned terms: " + ", ".join(f"{w} ({n})" for w, n in terms) + "."

    if totals["high_open"]:
        n = totals["high_open"]
        suggestions.append({"title": f"Prioritize {n} open high-priority {_plural(n, 'ticket')}",
                            "evidence": f"{n} of {open_} unresolved matching {_plural(open_, 'ticket')} {'is' if n == 1 else 'are'} HIGH priority.",
                            "next_step": "Confirm urgency with staff and make sure each one has an assigned owner."})
    if group in ("category", "location", "department") and plan["metric"] == "count" and rows and total >= 3:
        top = rows[0]
        if top["tickets"] / total >= 0.3:
            step = {"category": action_for_category(top["label"]),
                    "location": f"Inspect conditions at {top['label']} with the departments involved before deciding on repairs.",
                    "department": f"Check {top['label']}'s open queue and staffing before reassigning work."}[group]
            suggestions.append({"title": f"Focus on {top['label']}",
                                "evidence": f"{top['label']} accounts for {top['tickets']} of {total} matching tickets ({100 * top['tickets'] / total:.0f}%).",
                                "next_step": step})
    if plan["metric"] == "avg_resolution" and avg is not None:
        timed = [r for r in rows if r.get("avg_resolution_hours") is not None]
        if len(timed) >= 2 and timed[0]["avg_resolution_hours"] >= 1.5 * avg:
            suggestions.append({"title": f"Review handling time for {timed[0]['label']}",
                                "evidence": f"Average {timed[0]['avg_resolution_hours']:.1f} hours versus {avg:.1f} hours across all matching tickets.",
                                "next_step": "Check where these tickets wait longest (before assignment or while in progress) before changing the process."})
    if group in TIME_GROUPS and len(rows) >= 2 and rows[-1]["tickets"] > rows[-2]["tickets"]:
        last, prev = rows[-1], rows[-2]
        suggestions.append({"title": f"More tickets in the latest {group}",
                            "evidence": f"{last['label']}: {last['tickets']} tickets versus {prev['tickets']} in {prev['label']} (the latest {group} may be incomplete).",
                            "next_step": "Check whether the increase comes from one category or location before acting."})
    if total >= 3 and open_ / total >= 0.5:
        suggestions.append({"title": "Reduce the open backlog",
                            "evidence": f"{open_} of {total} matching tickets are still unresolved.",
                            "next_step": "Review ownership and the next action for each open ticket."})
    if plan["metric"] == "list":
        stale = [r for r in rows if r["status"] in OPEN and r["age_hours"] > 72]
        if stale:
            oldest = max(r["age_hours"] for r in stale)
            suggestions.append({"title": "Follow up on long-open tickets",
                                "evidence": f"{len(stale)} listed open {_plural(len(stale), 'ticket')} {'is' if len(stale) == 1 else 'are'} older than 3 days (oldest {oldest:.0f} hours).",
                                "next_step": "Ask the assigned department for a status update on each."})
    if terms and terms[0][1] >= 3:
        word, n = terms[0]
        suggestions.append({"title": f"Recurring mention: '{word}'",
                            "evidence": f"'{word}' appears in {n} of {len(texts)} matching tickets (NLTK term frequency).",
                            "next_step": f"Read the tickets mentioning '{word}' together to check for one shared cause."})
    return summary, suggestions[:4]
