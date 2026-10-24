"""Common issues: group complaints that describe the same problem, from their own wording.

NLTK stems each ticket's title+description; the stemmed word or two-word phrase shared by
the most tickets becomes an issue, those tickets are set aside, and the search repeats.
This is transparent term grouping, not a trained similarity model.
"""

from collections import Counter

from nltk.util import ngrams

from .nlp import STOPWORDS, content_stems, stem, tokens
from .ticket_rules import action_for_category

# Words every complaint uses; they say nothing about which problem it is.
GENERIC = {stem(w) for w in """
complaint complain issue issues problem problems please fix fixed help request report reported need needs needed kindly
sir madam mam again also there here someone anyone thing things time times work working regard regarding happen happening
since still yet lot lots really very bad worse worst good proper properly campus college student students room area
""".split()}
MAX_ISSUES = 5
UNIGRAM_WEIGHT = 0.75  # a shared two-word phrase ("water leak") beats a lone word with the same count


def _terms(text, skip):
    words = [s for s in content_stems(text) if s not in GENERIC and s not in skip and len(s) > 2 and not s.isdigit()]
    # pairs are order-free so "food is stale" and "stale food" share one key
    return set(words) | {" ".join(sorted(pair)) for pair in ngrams(words, 2) if pair[0] != pair[1]}


def _surface(texts, phrase, skip):
    """Readable form of a stemmed key: the word order and spellings the reporters used most."""
    forms, orders = {}, Counter()
    wanted = set(phrase.split())
    for text in texts:
        for word in tokens(text):
            if word not in STOPWORDS:
                forms.setdefault(stem(word), Counter())[word] += 1
        words = [s for s in content_stems(text) if s not in GENERIC and s not in skip]
        orders.update(pair for pair in ngrams(words, 2) if set(pair) == wanted)
    order = orders.most_common(1)[0][0] if orders else phrase.split()
    return " ".join(forms[s].most_common(1)[0][0] if s in forms else s for s in order)


def _plural(n, word):
    return word if n == 1 else word + "s"


def find_common_issues(tickets, locations=()):
    """Return common issues, most widespread first.

    tickets: [{"ticket_number", "text", "reporter_id", "reporter_role", "location", "category", "status", "created_at"}]
    locations: configured location names; their words are ignored so "Hostel 1" is not an issue.
    """
    if not isinstance(tickets, (list, tuple)):
        raise ValueError("Tickets must be a list.")
    skip = {s for name in locations for s in content_stems(name)}
    terms = {i: _terms(t["text"], skip) for i, t in enumerate(tickets)}
    remaining = set(terms)
    issues = []
    while remaining and len(issues) < MAX_ISSUES:
        df = Counter(term for i in remaining for term in terms[i])
        scored = [((n if " " in term else n * UNIGRAM_WEIGHT), term) for term, n in df.items() if n >= 2]
        if not scored:
            break
        _, best = max(scored, key=lambda st: (st[0], " " in st[1], st[1]))
        members = sorted(i for i in remaining if best in terms[i])
        remaining -= set(members)
        group = [tickets[i] for i in members]
        issues.append(_describe(best, group, skip))
    return issues


def _describe(phrase, group, skip):
    texts = [t["text"] for t in group]
    name = _surface(texts, phrase, skip)
    reporters = {t["reporter_id"] for t in group}
    students = {t["reporter_id"] for t in group if t["reporter_role"] == "STUDENT"}
    open_count = sum(t["status"] in ("SUBMITTED", "IN_PROGRESS") for t in group)
    locations = Counter(t["location"] for t in group).most_common(3)
    category = Counter(t["category"] for t in group).most_common(1)[0][0]
    dates = sorted(str(t["created_at"])[:10] for t in group)
    n = len(group)

    where = ", ".join(f"{loc} ({c})" for loc, c in locations)
    summary = (f"'{name}' was reported {n} {_plural(n, 'time')} by {len(students)} {_plural(len(students), 'student')}"
               + (f" and {len(reporters) - len(students)} staff" if len(reporters) > len(students) else "")
               + f", mostly at {where}; {open_count} still open.")
    suggestions = [action_for_category(category)]
    if len(locations) > 1:
        suggestions.append(f"Check whether one cause links the reports at {', '.join(loc for loc, _ in locations)} before fixing each separately.")
    if len(reporters) == 1 and n > 1:
        suggestions.append("All reports come from one person; contact them directly to understand the full situation.")
    if open_count == 1:
        suggestions.append("Resolve the remaining open ticket and let every reporter of this issue know the outcome.")
    elif open_count:
        suggestions.append(f"Handle the {open_count} open tickets together and give every reporter the same update.")
    else:
        suggestions.append("All reports are closed; confirm with a few reporters that the problem has not returned.")
    return {
        "issue": name,
        "summary": summary,
        "times_reported": n,
        "reporters": len(reporters),
        "student_reporters": len(students),
        "open": open_count,
        "category": category,
        "locations": [{"location": loc, "count": c} for loc, c in locations],
        "first_reported": dates[0],
        "last_reported": dates[-1],
        "ticket_numbers": [t["ticket_number"] for t in group][:20],
        "suggestions": suggestions,
    }
