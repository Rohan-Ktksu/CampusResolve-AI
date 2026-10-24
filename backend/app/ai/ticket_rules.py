"""Conservative keyword triage against the institution's supplied configuration.

These are transparent rules, not trained AI. Mixed/unknown issues stay in review.
"""

import re
import unicodedata
from collections.abc import Mapping


# label aliases, complaint phrases, staff-facing investigation step
RULES = {
    "wifi": (
        ("wi fi", "wifi", "network", "internet"),
        ("wi fi", "wifi", "internet", "network", "router", "connectivity", "bandwidth"),
        "Test connectivity at the reported location and review network service logs before deciding on a repair.",
    ),
    "equipment": (
        ("classroom equipment", "equipment", "projector", "computer"),
        ("projector", "smart board", "classroom screen", "classroom computer", "classroom equipment"),
        "Have authorized staff inspect the affected classroom equipment and arrange an alternative if needed.",
    ),
    "electrical": (
        ("electrical", "electricity", "power"),
        ("sparks", "sparking", "exposed wire", "exposed wires", "socket", "electric shock",
         "power outage", "power cut", "no power", "short circuit", "lights not working", "fan not working", "electrical fault"),
        "Ask qualified facilities staff to inspect the reported electrical fault; reporters should not attempt repairs.",
    ),
    "plumbing": (
        ("plumbing", "water", "drainage"),
        ("water leak", "leaking tap", "leaking pipe", "pipe", "tap", "blocked drain", "clogged drain",
         "water supply", "no water", "toilet blocked", "flooding", "sewage", "plumbing"),
        "Have facilities staff inspect the reported water or drainage issue and verify service after repair.",
    ),
    "cleanliness": (
        ("cleanliness", "housekeeping", "sanitation", "waste"),
        ("garbage", "litter", "dirty", "unclean", "overflowing bin", "sanitation", "cleaning", "waste", "cleanliness"),
        "Inspect the reported area, arrange cleaning or waste collection, and verify completion with the reporter.",
    ),
    "transport": (
        ("transport", "bus", "shuttle"),
        ("bus", "shuttle", "transport"),
        "Check the affected route and service records with transport staff before changing the schedule or fleet.",
    ),
    "hostel": (
        ("hostel", "mess"),
        ("mess food", "hostel food", "hostel service"),
        "Ask hostel services to inspect the reported service issue and confirm the corrective action.",
    ),
    "library": (
        ("library", "books"),
        ("library book", "book issue", "library access", "missing book"),
        "Ask library staff to verify the affected service or resource and communicate the next action.",
    ),
    "infrastructure": (
        ("infrastructure", "maintenance", "facilities"),
        ("broken door", "broken window", "damaged wall", "broken desk", "ceiling leak", "roof leak",
         "broken bench", "pothole", "infrastructure"),
        "Inspect the damaged facility, document its condition, and assess repair needs before proposing replacements.",
    ),
}

HAZARDS = ("fire", "smoke", "sparks", "sparking", "exposed wire", "exposed wires",
           "electric shock", "gas leak", "sewage overflow", "flooding")


def _normalize(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.translate(str.maketrans({c: " " for c in "-_/\u2010\u2011\u2012\u2013\u2014\u2015"}))
    return " ".join(value.split())


def _has(text, phrase):
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def _family(name):
    normalized = _normalize(name)
    for family, (labels, _, _) in RULES.items():
        if any(_has(normalized, label) for label in labels):
            return family
    return None


def action_for_category(name):
    family = _family(name)
    return RULES[family][2] if family else "Review representative reports with the responsible team and inspect the affected service before deciding on improvements."


def _rows(values):
    if not isinstance(values, (list, tuple)):
        raise ValueError("Configuration must be a list of records.")
    active = []
    seen = set()
    for row in values:
        if not isinstance(row, Mapping):
            raise ValueError("Configuration records must be mappings.")
        identifier = row.get("id")
        name = row.get("name")
        if type(identifier) is not int or identifier < 1 or identifier in seen:
            raise ValueError("Configuration IDs must be unique positive integers.")
        if not isinstance(name, str) or not name.strip() or len(name) > 160:
            raise ValueError("Configuration names must be nonempty strings of at most 160 characters.")
        seen.add(identifier)
        if row.get("is_active", True) is True:
            active.append(row)
    return active


def _hazard(text):
    for phrase in HAZARDS:
        for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text):
            prefix = text[max(0, match.start() - 35):match.start()]
            if not re.search(r"(?:\bno(?: signs? of)?|\bwithout|\bnot)(?: (?:a|an|any))?\s*$", prefix):
                return True
    return False


def analyze_complaint(title, description, allowed_categories, departments):
    """Return the agreed AIAnalysis dict, without changing inputs or ticket state."""
    for value, limit in ((title, 160), (description, 5000)):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError("Complaint text is missing, invalid, or exceeds the contract limit.")
    categories = _rows(allowed_categories)
    department_ids = {row["id"] for row in _rows(departments)}
    text = _normalize(title + ". " + description)
    matched = {family for family, (_, words, _) in RULES.items() if any(_has(text, word) for word in words)}
    configured_families = {_family(row["name"]) for row in categories}
    candidates = []
    for row in categories:
        family = _family(row["name"])
        matches = family in matched
        # Generic Infrastructure can cover specific facility faults only if no
        # configured specific category already covers that fault.
        if family == "infrastructure":
            matches |= any(f in matched and f not in configured_families for f in ("electrical", "plumbing", "equipment"))
        if family is None and _normalize(row["name"]) not in {"other", "general", "uncategorized"}:
            matches = _has(text, _normalize(row["name"]))
        if matches:
            candidates.append(row)

    # ponytail: literal rules cannot resolve mixed reports or infer root causes;
    # keep ambiguous cases for people rather than fabricating model confidence.
    chosen = candidates[0] if len(candidates) == 1 and len(matched) <= 1 else None
    hazard = _hazard(text)
    priority = "HIGH" if hazard else "NORMAL"
    if chosen and not hazard:
        if any(_has(text, p) for p in ("whole campus", "entire building", "all classrooms", "during exam", "during an exam", "during assessment")):
            priority = "HIGH"
        elif any(_has(text, p) for p in ("cosmetic", "minor scratch", "faded sign", "paint peeling")):
            priority = "LOW"

    mapped = chosen.get("default_department_id") if chosen else None
    department_id = mapped if type(mapped) is int and mapped in department_ids else None
    actions = []
    if hazard:
        actions.append("Keep people clear of the reported hazard and contact campus safety or qualified staff promptly.")
    if chosen:
        actions.append(action_for_category(chosen["name"]))
        reason = f"Keyword rules matched the configured category '{chosen['name']}'."
        if department_id is not None:
            reason += " Department suggestion follows its configured routing rule."
        else:
            reason += " No active configured department mapping is available; an administrator must route it."
    else:
        reason = "Rules matched multiple issue types or configured categories; split or review the issues." if candidates else "No clear configured category matched; review manually."
        actions.append("Confirm the issue, exact location, and impact with the reporter before assigning a department.")
    actions.append("An authorized person should verify the suggested handling and confirm the work before resolution.")
    return {
        "category_id": chosen["id"] if chosen else None,
        "suggested_department_id": department_id,
        "priority": priority,
        "summary": " ".join(title.split()),
        "reason": reason,
        "suggested_actions": actions,
        "source": "rules",
        "needs_review": chosen is None or department_id is None or priority == "HIGH",
    }
