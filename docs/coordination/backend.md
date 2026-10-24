# Atif / backend

State: FROZEN. Sonia ACCEPTED the same hash in origin/feature/frontend 1f0c800; verified on 2026-10-24 that origin/feature/backend:docs/openapi.json hashes to it. Further changes go through the same review process.
Contract SHA-256 (docs/openapi.json, LF): d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c
Contract version: 0.2.0
Branch: feature/backend

## Proposal summary for Sonia

No endpoint or schema shape changed from the seed v0.1. v0.2 only fixes routine semantics, listed at the top of docs/API_CONTRACT.md: ticket format `CMP-000042`, `image_url` value, location must come from `GET /locations`, list ordering, token lifetime, seeded demo accounts, and the rules-only analyze fallback.

Review with:

```
git fetch origin
git show origin/feature/backend:docs/openapi.json > work/openapi.json
Get-FileHash work/openapi.json -Algorithm SHA256
```

Record ACCEPTED plus the identical hash in docs/coordination/frontend.md, or numbered CHANGES_REQUESTED with JSON examples.

Frontend notes:
- History entries come from two tables, so `id` is unique only per `kind`; use `kind + id` as the React key.
- Login uses the seeded accounts in docs/API_CONTRACT.md. Show `location` as a dropdown from `GET /locations`.
- The backend is ready to run locally now; see backend/README.md.

## Implemented (all 31 contract operations are live)

Login/me (HS256 bearer, PBKDF2 password hashes), institution/locations, admin category/department CRUD with soft deactivation, staff list, complaint create/list/get/patch/archive, category-rule department routing, JPEG/PNG upload validated by file signature (<=5 MiB, authorized serving, stored outside any public folder), assignment, status workflow with history, reporter-only feedback CRUD, dashboard stats, insights, rules report, analyze.

AI wiring: routes call `app.ai.analyze_complaint` and `app.ai.generate_admin_report` if Rohan's package exports them, validate the output (schema plus configured IDs), and otherwise return labelled `source: "rules"` output. As of origin/feature/ai at cde640d, neither function exists, so the output is always rules.

## Tests actually run by Atif (2026-10-24, Linux, Python 3.14.6, PostgreSQL 16 in local podman)

- `python scripts/check_contract.py` → "Contract sanity check passed: 31 operations".
- `cd backend && python -m pytest -q` → 8 passed. Covers: unauthenticated/invalid-token 401, unknown fields 422, student+staff reporting, rule routing, invalid and oversized image rejection, valid upload with authorized fetch, another student/other department 404, role 403s, assignee must belong to department, invalid/same-state transitions 409, outcome note required, resolved_at set, history order, feedback CRUD + duplicate 409, stats average, uncategorized → review, reject, category change reroutes, admin-only archive, config deactivation blocks new use, foreign-institution department rejected, 16 concurrent creates → 16 unique ticket numbers, analyze rules fallback, insights range validation, empty-period report.
- Runtime: `python scripts/check_contract.py work/runtime-openapi.json` → "Runtime exposes every seed operation".
- Restart persistence: created CMP-000001 via curl, restarted uvicorn, ticket still listed.

## Integration with Sonia's frontend (origin/feature/frontend 1f0c800, run by Atif on 2026-10-24)

- Checked out read-only in a temporary worktree; no frontend files changed. `npm install && npm run build` → built (208.66 kB JS).
- Ran the backend (uvicorn :8000) and `vite --port 5173` with its `/api` proxy, then used the UI in a browser:
  student submitted a Wi-Fi report → CMP-000002 row in PostgreSQL, rule-routed to IT → admin got rules-labelled AI suggestions and assigned IT Staff → IT staff marked IN_PROGRESS, then RESOLVED with a note and the verification checkbox → student submitted a 5★ rating (feedback row in DB) → `/dashboard/stats` via the proxy: resolved_count 1, avg_resolution_hours 0.03 (2 min 5 s actual).
- Server log during the run: one non-2xx response, the expected 404 from `GET /complaints/2/feedback` before feedback existed.

## Gaps / not yet verified

- Not run on Windows yet; commands in backend/README.md are written for it but untested there.
- Image upload and Insights/report were exercised by API tests, not through the UI in this run.
- Runtime schemas were compared by operation presence only, not field by field.
- Image check uses file signatures, not full decoding.

Review responses: ACCEPTED d32af66a… (origin/feature/frontend 1f0c800). No changes requested.

Next: when Sonia's review lands, address it and re-propose if the contract changes; help integrate the first real frontend submission.
