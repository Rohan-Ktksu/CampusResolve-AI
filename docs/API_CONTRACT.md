# API contract — v0.2 PROPOSED by Atif, awaiting Sonia's review

Canonical machine contract: docs/openapi.json. Atif owns it; Sonia reviews it using docs/coordination/README.md. The Markdown defines workflow/access semantics that JSON schemas alone cannot express. Both must agree. Implementation lives in backend/ on feature/backend; see docs/coordination/backend.md for what is actually running and tested.

## v0.2 backend decisions (routine details, no wire-shape change from v0.1)

- `ticket_number` is `CMP-` plus the zero-padded database ID, e.g. `CMP-000042`, enforced unique in PostgreSQL.
- `image_url` is `null` until an upload succeeds, then the relative path `/api/v1/complaints/{id}/image`. Fetch it with the bearer token and show it as a blob URL; it is not a public link.
- `location` must exactly equal a `name` from `GET /locations`, otherwise 422. Use a dropdown so insights do not fragment on spelling.
- `GET /complaints` returns newest first. `mine=true` limits to the caller's own reports. Staff without `mine` see their departmental queue plus their own reports.
- Access tokens are HS256 bearer tokens valid for 8 hours; an expired/invalid token returns 401.
- Seeded demo accounts (fictional institution `DEMO`, password `demo1234` for all, local prototype only): `student@demo.edu` (STUDENT), `student2@demo.edu` (STUDENT), `it.staff@demo.edu` (STAFF, IT), `facilities.staff@demo.edu` (STAFF, Facilities), `coordinator@demo.edu` (COORDINATOR), `admin@demo.edu` (ADMIN).
- `POST /complaints/{id}/analyze` returns `source: "rules"` with `needs_review: true` manual-review output until Rohan's `app.ai.analyze_complaint` exists; the route never changes the ticket.

## Wire conventions

- Full paths begin /api/v1. JSON request/response; image upload is multipart field `file`.
- Numeric IDs; UTC ISO-8601 timestamps; arrays for lists; no pagination in the small demo.
- Bearer authentication; login returns access_token, token_type='bearer', and user with role/institution/department. Verify identity on the backend, never accept client-selected tenant or reporter.
- Browser sessionStorage holds prototype tokens for the same-origin demo. All views use the same API client. Expired tokens return to login; logout clears the token. This is not a production session/SSO design.
- Optional input fields are marked in OpenAPI. Unknown fields are rejected. PATCH /complaints requires at least one permitted field; configuration PATCH and feedback PATCH use their documented complete request models for simplicity.
- 401 unauthenticated; 403 forbidden action; 404 missing/inaccessible resource; 409 workflow or duplicate conflict; 422 invalid input. Error detail is string or validation list. No success body on 204.

## Endpoint access and behavior

| Endpoint | Behavior / access |
|---|---|
| POST /auth/login; GET /auth/me | Anonymous login; authenticated identity |
| GET /institutions/current; GET /locations | Authenticated current institution and seeded canonical campus location names |
| GET /categories; GET /departments | Active institution configuration for authenticated users |
| POST /categories, /departments | ADMIN creates |
| PATCH /categories/{id}, /departments/{id} | ADMIN updates |
| DELETE /categories/{id}, /departments/{id} | ADMIN deactivates; 204, preserve historical references |
| GET /staff?department_id=... | ADMIN/COORDINATOR lists valid active departmental assignees |
| POST /complaints | STUDENT/STAFF reports; category optional; apply configured routing |
| GET /complaints | Visible nonarchived records; optional status/category_id/mine filters never widen access |
| GET /complaints/{id} | Reporter or authorized operational staff |
| PATCH /complaints/{id} | Reporter edits title/description/location/category while SUBMITTED; ADMIN/COORDINATOR may edit category/priority while nonterminal; staff cannot self-promote authority through fields |
| DELETE /complaints/{id} | ADMIN soft archive; 204; preserve history |
| POST /complaints/{id}/image | Original reporter while SUBMITTED; actual JPEG/PNG, <=5 MiB; replace one attachment, return updated complaint |
| GET /complaints/{id}/image | Same visibility as complaint; authenticated binary fetch; no public uploads folder |
| PATCH /complaints/{id}/assign | ADMIN/COORDINATOR, nonterminal only; department required, staff optional and belongs to department |
| PATCH /complaints/{id}/status | ADMIN/COORDINATOR or authorized assigned-department staff; workflow below |
| GET /complaints/{id}/history | Same visibility as complaint; chronological combined status/assignment events |
| POST/GET/PATCH/DELETE /complaints/{id}/feedback | Original reporter only, RESOLVED only; one rating 1–5; absent GET=404, duplicate POST=409; DELETE=204 |
| GET /dashboard/stats | ADMIN/COORDINATOR institution-wide aggregates |
| POST /complaints/{id}/analyze | ADMIN/COORDINATOR suggestions only; optional enhancement, no state changes |
| GET /dashboard/insights?from=...&to=... | Optional ADMIN/COORDINATOR aggregates |
| POST /dashboard/insights/report | Optional ADMIN/COORDINATOR on-demand report; input dates only, never browser totals |

## Roles and workflow

Staff can report their own issues and separately work their departmental queue. Queue access requires active same-institution membership in assigned_department_id and either no named assignee or that user as assignee. ADMIN/COORDINATOR handles the institution-wide queue. STUDENT sees only own reports. Images and history inherit ticket visibility.

SUBMITTED -> IN_PROGRESS or REJECTED; IN_PROGRESS -> RESOLVED or REJECTED. IN_PROGRESS requires a department. RESOLVED/REJECTED requires nonempty note. Same-state/reopening requests return 409. Set resolved_at only on actual resolution. Transactionally append status/assignment history, including rule-based assignment and category-driven reassignment. Category changes reapply the configured rule (or clear department and route to review), clearing incompatible named assignees. Category and department references must be active and institution-local for new assignments; terminal/history references remain intact when config is deactivated.

Use PostgreSQL-generated complaint IDs to derive display ticket_number; do not use row count + 1. Use actual database constraints for uniqueness. Reject client changes to reporter, tenant, ticket number, timestamps, image path, or status through generic PATCH.

## Metrics and reports

Basic stats exclude archived complaints. Average resolution hours uses resolved_at - created_at across resolved records; empty average is null, with resolved_count=0. P0 includes total/status/category counts and resolution time.

Optional Insights uses complaint created_at in the selected UTC date range, inclusive from-date and through the whole to-date (end boundary is next day, exclusive). Counts reflect current status of that cohort at generated_at, not historical status snapshots. Require from<=to and a bounded range of at most 366 days. Rohan's report uses the same cohort. Frontend clearly displays this cohort definition.

Group by configured category and canonical location name. Missing category displays Uncategorized. Show frequent categories separately from high-priority unresolved backlog. No trends in v0.1; add comparable previous-period data and contract review before claiming increases/decreases. Recommendations must cite supplied figures and cannot establish causes or spending requirements. Staff validates priority signals; no automatic capital-development decisions.

## Example create

```json
{"title":"Wi-Fi unavailable","description":"The network disconnects during lab.","location":"Block B / Lab 204","category_id":2}
```

Response: 201 Complaint from OpenAPI, including id, ticket_number, owner, current assignment/status, null image_url until successful upload, and timestamps. A configured category rule may already assign a department. Images are uploaded in a second request; upload failure leaves the ticket available with a retry action.

## Agreement and verification

Run `python scripts/check_contract.py` and record the SHA-256 of docs/openapi.json. This sanity check resolves local references and required path parameters; it is not full OpenAPI/schema validation or proof of implemented behavior. After backend exists, save its actual /openapi.json to work/runtime-openapi.json and optionally compare operation presence using `python scripts/check_contract.py work/runtime-openapi.json`. Then compare schemas and run actual authorized lifecycle checks. Do not treat stub/mocked responses as completed integration.
