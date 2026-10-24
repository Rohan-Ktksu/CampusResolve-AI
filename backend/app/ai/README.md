# Rohan's local assistance package

Exports:

```python
from app.ai import analyze_complaint, describe_result, find_common_issues, generate_admin_report, parse_query

analysis = analyze_complaint(title, description, allowed_categories, departments)
report = generate_admin_report(authorized_backend_aggregates, complaint_texts)
parsed = parse_query("unresolved food complaints in Hostel 1 last month", categories, departments, locations)
summary, suggestions = describe_result(plan, totals, rows, texts, filter_labels)
issues = find_common_issues(tickets, locations)
```

One dependency: `nltk` (pip only; `nlp.py` uses the stemmer, tokenizer, n-grams and edit distance, which need no `nltk.download`). No network calls, model download, paid inference, database writes, or API keys. Output is labelled `source: nlp`. This is deterministic keyword analysis; a language model has not been installed or evaluated.

- `nlp.py`: shared tokenizing, stemming, typo-tolerant phrase matching (any word order within a short window; one edit for 6+ letter words, two for 8+), and most-mentioned terms.
- `query_rules.py`: admin chatbox parser (dates such as "last month", "since 2026-10-01", "in september"; status, priority, grouping, top N; locations before categories so "Hostel 1" is a place but "hostel complaints" is the Hostel category) and result summaries/suggestions.
- `issue_rules.py`: common issues with times reported, distinct student/staff reporters, open count, locations and suggestions.

## Ticket assistance

Returns configured category/department IDs, priority, the normalized title as an extractive summary, an explanation, suggested staff investigation steps, and needs_review. Supports Wi-Fi/network, classroom equipment, electrical, plumbing, cleanliness, housekeeping, transport, food/canteen, hostel, safety/security, library, academics, sports, and generic infrastructure where those categories are configured. Food poisoning, harassment, assault and similar reports are flagged HIGH. Custom categories require an explicit label match.

Unknown/mixed reports do not force an assignment. Missing/inactive department mapping gives a category suggestion with null department and needs_review=true. Literal reported safety hazards and broad exam/building impact are flagged HIGH for human verification. Stemming and edit distance tolerate word forms and small typos; unknown wording, sarcasm, negation outside hazards, and nuanced urgency remain limitations of keyword matching. This package cannot diagnose root causes, establish safety, or perform physical repairs.

Configured routing takes precedence; no invented departments or guessed IDs. Atif's updated backend seed includes Transport and the Main Gate / Bus Stop location; these are available after his startup configuration runs. A text match alone never changes ticket status or assignment.

## Admin report

Uses the backend's period/sample/counts, not raw student text. Separates high-priority unresolved reports from category frequency, sums location groups to find a hotspot, and provides at most three evidence-backed next actions. Reports describe current status within the selected creation-date cohort. No trend, cost, root-cause, or development-benefit claim is inferred from frequency alone.

Empty periods produce no recommendations. Invalid/inconsistent aggregate counts or timestamps raise, allowing Atif's route to fall back. Report department_id remains null because the agreed Insights input has no department map. The admin selects a responsible team; the output does not invent its identity.

Uncategorized reports remain in totals but are identified as a classification gap, not a recurring service category. Known categories are ranked separately; if none exists, the report asks for classification before service-development conclusions. A single report is not called recurring, and single-ticket counts use singular wording.

## Checks

From the repo root, with only Python:

```powershell
python -m unittest discover -s tests/ai -v
```

The cases cover actual demo categories, custom mappings, Unicode Wi-Fi text, word boundaries, simple hazard negation, urgency, unknown/mixed text, inactive/invalid IDs, untrusted instructions, input immutability, count consistency, no-data/empty-average states, deterministic sorting, and field compatibility with the wire contract.

`tests/ai/check_backend_adapter.py` optionally imports Atif's real backend models and route functions from a temporary snapshot. Install his existing backend requirements, pass that snapshot's backend directory, and optionally a path for synthetic JSON output. It checks real route output validation, function selection (no silent fallback), no-data, and failure fallback. Database/auth inputs are mocked explicitly. It does not run PostgreSQL or validate the full live browser lifecycle.

No backend/frontend implementation is changed by this package. Merge the agreed backend and AI changes through normal review, then exercise both AI endpoints in the live UI with PostgreSQL. That live verification remains necessary before claiming the complete integration is finished.
