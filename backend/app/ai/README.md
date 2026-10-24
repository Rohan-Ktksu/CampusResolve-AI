# Rohan's local assistance package

Exports, unchanged from the agreed interface:

```python
from app.ai import analyze_complaint, generate_admin_report

analysis = analyze_complaint(title, description, allowed_categories, departments)
report = generate_admin_report(authorized_backend_aggregates)
```

No third-party dependencies, network calls, model download, paid inference, database writes, or API keys. All output has source=rules. These functions are deterministic keyword/evidence rules; a language model has not been installed or evaluated.

## Ticket assistance

Returns configured category/department IDs, priority, the normalized title as an extractive summary, an explanation, suggested staff investigation steps, and needs_review. Supports Wi-Fi/network, classroom equipment, electrical, plumbing, cleanliness, transport, basic hostel/library services, and generic infrastructure where those categories are configured. Custom categories require an explicit label match.

Unknown/mixed reports do not force an assignment. Missing/inactive department mapping gives a category suggestion with null department and needs_review=true. Literal reported safety hazards and broad exam/building impact are flagged HIGH for human verification. Unknown wording, sarcasm, negation, spelling mistakes, and nuanced urgency are limitations of keyword rules. This package cannot diagnose root causes, establish safety, or perform physical repairs.

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
