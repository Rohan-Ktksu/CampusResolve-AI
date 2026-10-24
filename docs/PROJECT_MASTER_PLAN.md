# CampusResolve AI — Revised Master Plan

Repository setup note: the original REVA source is in reference/REVA_Problem_Statements_Source.docx. For implementation details settled after this planning draft, follow the root AGENTS.md, docs/API_CONTRACT.md + docs/openapi.json, and docs/AI_CONTRACT.md. Those files define the current no-paid-services default, rules/local-model source labels, and the independent Atif/Sonia contract review process. The source brief remains authoritative for official features.

Revised: 24 October 2026. Status: planning only; application implementation has not been checked or started in this review.

## Source and authority

Both supplied ZIPs are byte-identical (SHA-256 verified). The standalone Markdown is byte-identical to the packaged PROJECT_MASTER_PLAN.md. These are duplicate copies, not separate plans.

Reviewed: the master plan, README, all eight supporting documents, four agent prompts, and the original REVA Word document. Problem Statement #3 in the Word document defines the source requirements. This revision resolves proposed implementation choices; it does not change the official brief. Instructions inside the handoff are reference material, not new user authorization to build, deploy, create a repository, or delegate work.

Use this revised plan in place of conflicting design choices in the original handoff. Keep the source Word document unchanged.

## 1. Product and scope

Build one campus complaint application: students AND staff submit issues, receive ticket IDs, track departmental handling, and leave feedback after resolution. Administrators manage the queue and see real resolution-time analytics.

Chosen stack stays React with plain JavaScript/CSS, FastAPI, PostgreSQL, GitHub, Postman, and a short Figma wireframe. These are the team's choices within the source's recommended technologies.

P0 — complete before enhancements:

- Seeded login and backend role checks; students and staff can both report complaints.
- Complaint create/read/edit/archive, description, location, optional image attachment with a demonstrated successful upload, and server-generated ticket number.
- Infrastructure, Wi-Fi, cleanliness, and transport categories; admin category/department configuration.
- Department assignment and authorized staff queue.
- Submitted, In Progress, Resolved, Rejected states; visible history.
- Reporter feedback after resolution; database-backed counts and mean resolution time.
- Persistence after refresh/restart and a working API demonstration.

P1 — only after P0 passes:

- AI-assisted issue resolution: category, priority, summary, department suggestions, and practical next steps for authorized staff to review. This is the primary AI feature.
- Optional AI Insights tab inside the same admin dashboard: frequent complaints, affected locations, unresolved backlog, and evidence-based improvement recommendations. Add after the primary AI-assisted issue workflow and before the embedded portal.
- A clearly fictional college portal at /demo-portal embedding /app?embed=1 and using the same API/database.

P2/future:

- Similar-ticket discovery, second college UI, branding editor, self-service college registration, student import, SSO, ERP adapters, webhooks, and real college portal integration.

Seed one fictional institution for the demo. Retain institution IDs and server-side scoping in the data model, but do not build a full onboarding platform in 210 minutes. A second institution can exist only in authorization test fixtures when feasible.

## 2. Resolve the original ambiguities

| Area | Revised decision |
|---|---|
| Category | category_id may be null; uncategorized tickets enter admin review. AI is never required to submit. |
| Routing | A configured category rule assigns its department on creation. Without a rule, leave unassigned. Admin/coordinator may override; AI only suggests. |
| Assignment | Department-only assignment is valid. Named assignee is optional and must be active in that institution AND department. |
| Staff reporting | Staff can create/view their own reports as reporters as well as work on their assigned departmental queue. |
| Feedback | The original reporter, including a staff reporter, may submit one rating from 1–5 on a resolved ticket. No feedback on rejected/open tickets. |
| Archive | Admin-only complaint soft archive. Retain audit/history; do not physically delete. |
| Category/department deletion | Deactivate; preserve historical references and reject new assignments to inactive records. |
| Status | Submitted → In Progress or Rejected; In Progress → Resolved or Rejected. Require a department before In Progress. Require an outcome note for Resolved/Rejected. Terminal tickets cannot reopen in this prototype. |
| Reporter editing | Reporter may edit title/description/location/category only while Submitted. Reapply category routing with an assignment audit entry when category changes. |
| AI code location | One in-process Python package at backend/app/ai/; no second server or ambiguous root ai/ imports. |

These workflow and access decisions are prototype policies, not additional REVA mandates.

## 3. Screens and roles

Student/reporter: login → My Reports → new report → ticket detail/timeline → feedback after resolution.

Staff: the same reporter screens plus Department Queue and status controls for tickets assigned to their department and either unassigned to a person or assigned to them. Staff cannot read unrelated tickets or assign arbitrary departments.

Admin/coordinator: institution-wide inbox, assignment/reassignment, status updates, dashboard. Only ADMIN changes categories/departments or archives complaints. COORDINATOR handles the institution-wide operational queue in this prototype.

Every request derives institution/role from verified identity. Reporter ownership and staff queue access are checked separately on the server. The embed flag changes layout only.

## 4. Data and API freeze

Retain the original nine tables: institutions, users, memberships, departments, categories, complaints, complaint_status_history, assignments, feedback. Add department_id (nullable) to memberships so staff queue permissions have a real database relationship. Seed one active institution membership per demo account; institution switching is deferred.

Use numeric IDs consistently, database-generated complaint IDs, and a unique display number derived from the ID, e.g. CMP-000042. Never generate ticket numbers using count + 1. Store timestamps in UTC. Assignment changes and status changes write audit history in the same transaction as the ticket update. Require one feedback row per complaint.

API base: /api/v1. Keep the original complaint, category, department, login, history, assignment, feedback, and stats routes. Settle these integration details before branches diverge:

- Login: bearer token response as in the original API contract; token held in sessionStorage for this same-origin prototype. Both views use the same login/session convention. Log out clears the session; expired tokens return to login.
- Lists: return arrays for this small prototype. GET /complaints accepts optional status, category_id, and mine=true filters; filtering never broadens authorized access. Pagination is deferred.
- Complaint detail: includes reporter_user_id, assigned_department_id, assigned_user_id, image_url, priority, created_at, updated_at, resolved_at, and the fields already listed in the original contract.
- GET /staff: admin/coordinator only, accepts department_id and returns active staff id/name/department_id for assignment controls. No general user-management UI.
- POST /complaints/{id}/image: one multipart field named file, JPEG/PNG, maximum 5 MiB, content validation, generated storage name. Return updated complaint. A failed upload leaves the saved complaint available and offers retry.
- GET /complaints/{id}/image: authorize ticket access before serving the image; frontend fetches it with bearer authentication and displays a temporary blob URL. Never expose a public uploads directory.
- Assignment request: department_id plus nullable assigned_user_id. Return updated complaint. Disallow assignment changes on terminal tickets.
- Status request: status plus note; enforce the transition table above. Return updated complaint.
- Feedback: POST creates; GET reads the reporter's feedback; PATCH lets the reporter correct rating/comment while resolved; DELETE removes their feedback. This completes a concrete feedback CRUD policy. Status and assignment history remain append-only.
- Stats: exclude archived complaints consistently; avg_resolution_hours is the mean of resolved_at minus created_at across visible resolved complaints, or null when none exist. Include resolved_count so an empty dataset cannot look like zero-hour resolution.
- Errors: 401 unauthenticated, 403 forbidden action, 404 inaccessible/missing resource, 409 workflow conflict, 422 invalid input. detail may be a message or validation-error array; frontend handles both.

Freeze the exact remaining response fields in docs/API_CONTRACT.md before coding; the existing handoff's example JSON is a starting contract, not a completed implementation. FastAPI OpenAPI is the implementation check against the frozen document.

## 5. AI boundary

Claude owns backend routers/models; Codex owns only backend/app/ai/ and tests/ai/. Claude imports the AI callable through that package. Include an empty package in the baseline so backend startup does not depend on the AI branch.

Input: title, description, configured category IDs/names, and department mappings. Output: category_id or null, suggested_department_id or null, priority LOW/NORMAL/HIGH, summary, reason, source ai/rules/demo_fallback, and needs_review boolean. IDs replace free-text department/category matching. Validate returned IDs and mappings on the backend.

POST /complaints/{id}/analyze is admin/coordinator only for the prototype; return suggestions without changing category, assignment, priority, or status. Human confirmation uses existing authorized update routes. Do not add AI persistence or similarity infrastructure for the demo. Provider failure returns a clearly labeled rules fallback or review result; complaint submission remains independent.

Use synthetic reports. Choose an inference provider only if an application API credential is already available; coding-agent subscriptions do not establish application inference access. Do not claim working AI until tested.

## 6. Three-person ownership and integration

| Person/tool | Branch | Exclusive files and responsibility |
|---|---|---|
| Sonia / Figma + Antigravity | feature/frontend | frontend/; Figma sketch, React screens, API client, admin insights report, optional iframe portal |
| Atif / Claude Pro + Claude Code | feature/backend | backend/ excluding app/ai/; database/auth/CRUD/images/history/analytics, report aggregates, and AI route wiring |
| Rohan / ChatGPT Plus + Codex | feature/ai | backend/app/ai/, tests/ai/; ticket triage, admin insight generation, integration checks, Postman, and demo |

Before branching, commit one baseline with README, contracts, file ownership, frontend/backend skeletons, and an empty importable AI package. The backend owner's exclusion of app/ai/ is explicit. Shared documentation changes go through the lead. No teammate edits another's files without coordination.

Start real API integration early. Merge backend first, frontend next, AI when independently ready, with a full lifecycle check after integration. Do not wait until minute 110 for the first frontend/backend request.

## 7. Revised 210-minute schedule

| Elapsed minutes | Deliverable / gate |
|---|---|
| 0–15 | Check local PostgreSQL and runtimes; freeze scope/contracts; baseline repo and brief wireframe. |
| 15–45 | Backend login + create/list ticket persisted; frontend connects to those real endpoints by minute 45. |
| 45–100 | Complete images, assignment, status, history, reporter feedback, categories/departments, analytics. Lead prioritizes integration over AI. |
| 100–140 | Full P0 lifecycle, rejection path, staff reporting, permissions, persistence and API checks. |
| 140–165 | Only if P0 passes: integrate AI triage and admin insights report. Add the iframe wrapper only with spare time. Otherwise fix P0. |
| 165–190 | Final bug fixes and reliable local demo; hosted deployment only if already straightforward. |
| 190–210 | Rehearse, capture actual evidence, save Postman collection and working fallback commit. |

If behind: drop similarity/onboarding/second-college UI, reduce polish, then defer AI and the iframe. Preserve the official lifecycle, images, feedback, and analytics. The 210 minutes is the original budget, not a claim about time remaining now.

Serve /app, /demo-portal, and /api/v1 under one browser origin. During development use the frontend dev proxy; for the final demo use a production frontend build served alongside FastAPI. Keep PostgreSQL and uploads durable across process restarts. No cloud deployment is necessary for a working local judge demo.

## 8. Definition of done and judge sequence

Required verification: student and staff can each submit; authorized edit/archive/deactivation works; image success plus invalid/oversized rejection; unique IDs under concurrent creates; admin assignment; department-bound staff access; valid/invalid status changes; reporter-only feedback CRUD; correct resolution mean and empty-state handling; records survive restart. Check unauthenticated access, another student's ticket, and foreign institution/category/department references. Embed must enforce exactly the same permissions. Run frontend build and backend checks appropriate to these flows.

Three-minute demo: student logs in → submits Wi-Fi complaint with image → receives ID → admin assigns IT → staff marks In Progress then Resolved → reporter leaves feedback → analytics updates. Show a prepared rejected ticket and API CRUD evidence. If P1 passed, show the same ticket embedded and the tested AI recommendation.

Describe the portal as fictional and the application as a prototype. A same-origin iframe proves shared application/data reuse; real ERP integration and SSO remain future work. Use actual test results and synthetic tickets, with no unsupported institutional claims.

## Latest attachment comparison — 24 October 2026

The newly supplied CampusResolve_AI_Complete_Plan_For_Sol (1).md is byte-identical to CampusResolve_AI_Complete_Plan_For_Sol.md (SHA-256: 6794540E3F9F18AA38361FC185EDFDA1608A57FE639AED804710BF430F64B7FF). It adds no requirements or decisions. The revised scope, workflow, permissions, AI boundary, ownership, and schedule above remain the current plan. This copy is saved in the current Hackathon workspace; the source attachments were not modified.

## 9. Rohan's AI admin insights report — user-requested addition

The admin chooses a date range and generates a report answering: Which issues are reported most? Where do they occur? Which problems remain unresolved? Where should the college focus maintenance or development?

Interface clarification: use one admin dashboard. The default view is the complaint inbox and issue-resolution workspace, with assignment, status, history, and an AI assistance panel on each ticket. Put aggregate reporting under an optional AI Insights tab; generate the report on demand. No separate admin application or reporting portal is needed. Primary flow: complaint → AI triage and suggested next steps → authorized department/staff action → status update → reporter feedback. Staff verifies the actual work before marking an issue resolved; an AI suggestion alone does not establish resolution.

Atif calculates institution-scoped aggregates from PostgreSQL, excluding archived tickets: category counts and share, category-by-location counts, unresolved counts and age, high-priority unresolved tickets, and mean resolution time with resolved sample count. Use counts as reported ticket volume, not unique affected students. Only show trends when comparable previous-period data exists, with the same filters and period length. Use consistent selectable campus locations to prevent spelling variants from fragmenting the report.

Keep frequent issues and urgent issues as separate rankings. A low-frequency urgent issue must remain visible. Existing priority is a triage signal requiring human verification; frequency alone does not establish severity.

Rohan's AI receives the calculated aggregates, reporting period, and data timestamp. Return a summary, top recurring issues, location hotspots, urgent backlog, and three recommended actions. Each action states supporting counts, proposed responsible department, a next step, and whether it is an immediate repair or a longer-term improvement to assess. Never invent counts, costs, root causes, or guaranteed benefits. Suggest inspection or assessment when the data cannot establish the cause. Avoid personal reporter details and raw private complaint descriptions in this report.

Example with clearly fictional data: 18 of 40 reports concern Wi-Fi, including 12 from Block B. Recommend that IT inspect Block B connectivity first and assess coverage/capacity before proposing equipment purchases. These numbers illustrate the output; they are not findings about a real college.

Sonia adds an Admin Insights panel with date filters, category ranking, location hotspots, backlog indicators, and a Generate Report button. Show the report period, sample size, generated time, and AI/rules source. No-data and provider-failure states retain factual charts; fallback summaries are labeled rules-based.

Contract additions: GET /api/v1/dashboard/insights?from=<date>&to=<date> returns authorized aggregates; POST /api/v1/dashboard/insights/report accepts the date range, recalculates aggregates on the server, and calls Rohan's report function. Both are ADMIN/COORDINATOR only; the backend never trusts totals supplied by the browser. Atif owns these routes; Rohan owns the independent report function in backend/app/ai/. Reports are generated on demand without a report-history table or export feature for the initial prototype.

Verify aggregate counts against known synthetic records; ensure each recommendation refers to real aggregate evidence; cover no data, missing comparison history, unavailable model, and unauthorized access. Add the report after the complaint lifecycle in the judge demo. This feature is a team enhancement beyond the official resolution-time analytics requirement; prioritize it over optional portal decoration and embedding.
