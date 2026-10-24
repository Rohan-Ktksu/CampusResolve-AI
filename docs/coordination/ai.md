# Rohan / AI

State: READY_FOR_UI_INTEGRATION; initial live API integration verified by Atif, latest report wording fixes checked by Rohan
AI callable interface: ACKNOWLEDGED, unchanged from docs/AI_CONTRACT.md
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
- Run the live PostgreSQL/UI lifecycle with the AI package present, including image and Insights screens. See Atif's recorded API verification below; full combined UI verification remains pending.
- Atif's updated backend seed now includes Transport routing and Main Gate / Bus Stop, with additive startup configuration that preserves existing tickets. Rules still do not invent configuration.
- Keyword rules cannot reliably understand arbitrary wording, spelling mistakes, nuanced negation, or root causes. No trained model or accuracy percentage is claimed.
- Reporter assistance is advisory; authorized staff confirms handling and actual resolution. No cost/benefit or real college integration claims are made.

## Atif's integration review and Rohan's follow-up — 24 October 2026

Inspected the published docs/coordination/backend.md and backend/tests/test_ai_integration.py on feature/backend. Atif records a clean temporary integration with AI commit 0cc4797, 17 backend tests passed (including 9 real PostgreSQL/route AI cases), 19 AI unit tests, adapter checks, and live HTTP consumption of both functions. Environment: Fedora 44 / Python 3.14.6 / PostgreSQL 16.15 in local podman. These are Atif's recorded runs, not Windows/PostgreSQL runs performed by Rohan. His branch alone skips the 9 AI cases until the package is integrated.

Addressed the two package review findings: singular report wording throughout; Uncategorized remains in totals but is a classification gap instead of a competing service category. Known-category recommendations win ties; all-uncategorized data asks for classification first. Single reports are not called recurring. No signature/schema/contract-hash change. Department recommendations remain null intentionally because the input has no authorized map.

Rohan's updated Windows suite: 22 unit tests passed (19 existing + 3 regression cases for singular data, Uncategorized tie, and all-uncategorized data). Adapter checks also passed against a fresh temporary snapshot of backend 203eb7f with the updated AI package: both functions accepted by actual models/routes, no silent fallback, empty-period/error handling intact. Database/auth inputs were mocked explicitly. Live API tests should be repeated on the final integrated revision before the final UI demo. Known backend limitation remains with Atif: renamed seeded config names are recreated on restart; this package does not change seeding.

## v0.3 — admin chatbox, common issues, NLTK, new categories — 24 October 2026

Requested by Rohan (lead/repository owner), who asked for this change to cover both backend and frontend in one PR, implemented with Claude Code on branch `feature/admin-nlp-query`.

State: v0.3 PROPOSED, not frozen. Contract SHA-256 (docs/openapi.json, LF): `d726d73cd0401c2ca413fdf10d58cd9b8d80cc484044c33a64111220cb6ab720`, version 0.3.0. Additive: `POST /dashboard/query`, `GET /dashboard/common-issues`, `AdminReport.common_issues`, source `nlp`. Atif's backend.md and Sonia's frontend.md were not edited; their review of v0.3 happens on the PR.

Changed outside backend/app/ai/ at Rohan's direction: backend routes/models/seed (Atif's area) and the Ask & Reports tab, common-issues panel and source labels (Sonia's area).

Commands actually run (Linux container, Python 3.13.17, PostgreSQL 16, Node 22.22.0, nltk 3.9.1):

- `python scripts/check_contract.py` and with the live server's `/openapi.json`: passed, 33 operations; new schemas' properties/required match the runtime models.
- `python -m unittest discover -s tests/ai`: 39 tests OK (22 existing with source updated to `nlp` + 17 new).
- `cd backend; python -m pytest -q`: 22 passed (17 existing + 5 new chatbox/common-issue/new-category cases).
- `python tests/ai/check_backend_adapter.py backend`: passed.
- `cd frontend; npm run build; node test_frontend_contract.mjs`: passed.
- Browser run (Playwright + Chromium against uvicorn + Vite, 14 synthetic tickets): chatbox question → grouped table, chip removal re-runs the plan, dashboard common issues, report with common issues. Only console error: missing /favicon.ico (pre-existing).

Limitations: English only. The parser recognises configured names, the listed category keywords, statuses, priorities, grouping words and common date phrases; other text falls back to totals with a warning. Common issues are word/phrase grouping, not semantic similarity, so differently worded reports of one problem can land in separate issues. Reporter counts are distinct accounts, not verified people. Complaint text is analysed but never quoted (AI_CONTRACT). New departments have no seeded staff accounts; admins/coordinators can still route and progress their tickets.
