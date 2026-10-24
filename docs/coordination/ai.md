# Rohan / AI

State: IMPLEMENTED_READY_FOR_REVIEW; live integration not yet run by Rohan
AI callable interface: ACKNOWLEDGED, unchanged from backend/app/ai/README.md
Branch: feature/ai

## Contract acknowledgement

- Atif's v0.2 contract is frozen and Sonia's review records ACCEPTED.
- Independently calculated SHA-256 of the published backend Git blob: d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c (matches both records).
- Inspected backend snapshot origin/feature/backend at e373892 and frontend review at c5063f8 on 24 October 2026.
- No endpoint, response model, permission, or callable-signature changes requested.

## Implemented by Rohan

- app.ai.analyze_complaint(title, description, allowed_categories, departments): rules-based category, mapped department, priority, extractive summary, explanation, suggested investigation steps, and manual-review flag.
- app.ai.generate_admin_report(aggregates): evidence-backed urgent backlog, frequent category, and location hotspot recommendations; no-data handling; at most three actions.
- All outputs source=rules. No model download, external requests, paid inference, database write, or ticket state change.
- Unknown/mixed/unconfigured issues remain in review. Active configured routing is authoritative. Report department_id=null because the frozen aggregate input contains no authorized department map.

## Tests actually run by Rohan (Windows, Python 3.12.10)

- `python -m unittest discover -s tests/ai -v`: 19 tests passed, including seeded category names, synthetic transport/custom routing, Unicode/word boundaries, simple hazard negation, urgency, unknown/mixed issues, invalid/inactive/dangling IDs, input immutability, untrusted text, report evidence, hotspot group sums, no data, and invalid aggregates.
- `python scripts/check_contract.py`: 31-operation seed contract sanity check passed. The frozen v0.2 Git blob hash was independently checked as above; local source contract has not been overwritten.
- `python -m compileall -q backend/app/ai tests/ai`: passed.
- Installed Atif's existing backend requirements into ignored local .venv for compatibility checks; the assistance package itself has no third-party dependency.
- ` .\.venv\Scripts\python.exe tests/ai/check_backend_adapter.py work/backend-integration/backend outputs/AI_Backend_Adapter_Synthetic_Demo.json`: passed against a temporary snapshot of Atif's backend with our AI functions. Real Pydantic models and route functions accept outputs without silent fallback. Verified empty-period and function-error fallbacks. Database/auth inputs were mocked explicitly, so this is not a live API/PostgreSQL/browser test.

## Remaining integration / limitations

- Review/merge the backend and AI PRs through Rohan; no main merge is authorized or performed by this handoff.
- Run the live PostgreSQL/UI lifecycle with the AI package present, including image and Insights screens. Atif reported a prior live lifecycle test without Rohan's package; that is not evidence for this new integration.
- Current backend seed omits Transport. Configure that category/department through the admin UI before demonstrating the official transport requirement; rules do not invent configuration.
- Keyword rules cannot reliably understand arbitrary wording, spelling mistakes, nuanced negation, or root causes. No trained model or accuracy percentage is claimed.
- Reporter assistance is advisory; authorized staff confirms handling and actual resolution. No cost/benefit or real college integration claims are made.
