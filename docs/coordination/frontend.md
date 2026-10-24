# Sonia / frontend

State: ACCEPTED
Reviewed contract SHA-256: d726d73cd0401c2ca413fdf10d58cd9b8d80cc484044c33a64111220cb6ab720
Contract version: 0.3.0
Branch: feature/frontend (reviewed v0.3 on `feature/admin-nlp-query` / PR #5 `cd8b2c9`)

## Contract v0.3 review summary (`cd8b2c9`)

- Inspected `docs/API_CONTRACT.md` ("v0.3 additions") and `docs/openapi.json` (version `0.3.0`, 33 operations).
- Verified `Get-FileHash docs/openapi.json -Algorithm SHA256` and Git blob SHA-256: `d726d73cd0401c2ca413fdf10d58cd9b8d80cc484044c33a64111220cb6ab720`.
- **Decision: `ACCEPTED`** (`d726d73cd0401c2ca413fdf10d58cd9b8d80cc484044c33a64111220cb6ab720`).
- Verified full frontend compatibility with all additive v0.3 changes:
  1. `source: "nlp"` badge support in `TicketWorkspace.jsx`, `AdminDashboard.jsx`, `AdminQueryChat.jsx`, and `CommonIssues.jsx` (`source: nlp (NLTK keyword analysis)` / `(NLTK text analysis)` alongside `source: rules`).
  2. `POST /api/v1/dashboard/query` (`api.askDashboardQuery`) wired to the **4. Ask & Reports** sub-tab (`AdminQueryChat.jsx`), supporting English question prompts (`{ text }`) and interactive filter-chip removal re-runs (`{ plan }`), sortable/filterable report table, CSV export, AI suggestions, and `Common Issues in These Tickets`.
  3. `GET /api/v1/dashboard/common-issues?from=...&to=...` (`api.getCommonIssues`) wired to `CommonIssuesPanel` in **2. Resolution Analytics** (`Common Issues From Complaint Descriptions` with `Main issue` headline) and `AdminReport.common_issues` in **3. AI Insights**.
  4. Additive seeded categories (`Infrastructure`, `Food / Canteen`, `Hostel`, `Safety / Security`, `Housekeeping`, `Library`, `Academics`, `Sports`) and departments (`Food Services`, `Hostel Office`, `Campus Security`).
- Live v0.3 verification run on Windows (`cd8b2c9` deployed to `https://literacy-saturn-done-licence.trycloudflare.com`):
  - `python scripts/check_contract.py` -> **33 operations passed**
  - `python -m unittest discover -s tests/ai` -> **39 tests passed in 0.666s**
  - `cd backend; python -m pytest -q` -> **22 passed in 11.15s**
  - `cd frontend; npm run build; node test_frontend_contract.mjs` -> **passed** (`32 modules transformed`, 17 endpoint groups verified)
  - Public tunnel browser E2E (`verify_v03_tunnel.mjs`): verified all new categories/departments, `4. Ask & Reports` example query + filter chip removal re-run, `2. Resolution Analytics` Common Issues + `MAIN ISSUE` line, `3. AI Insights` report with `Common Issues` section and `source: nlp`, student `"Stale food at lunch"` submission (`CMP-000042`) triaged to `Food / Canteen -> Food Services` (`source: nlp`), and `/demo-portal` iframe with `4. Ask & Reports`.

## Contract v0.2 review summary (from `origin/feature/backend`)

- Fetched `origin/feature/backend` (`6c73887`) and inspected `docs/API_CONTRACT.md`, `docs/openapi.json`, and `docs/coordination/backend.md`.
- Verified `origin/feature/backend:docs/openapi.json` SHA-256 is `d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c`.
- **Decision: `ACCEPTED`** (`d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c`).
- Incorporated all v0.2 frontend alignment notes into `frontend/`:
  1. History timeline uses composite React key `` `${h.kind}-${h.id}` `` because status and assignment history entries originate from two tables (`complaint_status_history` and `assignments`).
  2. Location fields on both the Report Issue form and Reporter Edit form use a `<select>` dropdown bound to canonical `name` values from `GET /api/v1/locations`.
  3. Login screen includes quick-fill helpers for the seeded `DEMO` accounts (`student@demo.edu`, `student2@demo.edu`, `it.staff@demo.edu`, `facilities.staff@demo.edu`, `coordinator@demo.edu`, `admin@demo.edu`, password `demo1234`) while authenticating via `POST /api/v1/auth/login`.
  4. Image display uses authenticated `GET /api/v1/complaints/{id}/image` with the Bearer token and renders a temporary `Blob` URL (`URL.createObjectURL`), with upload retry preserved if `POST /api/v1/complaints/{id}/image` fails after `POST /api/v1/complaints` succeeds.
  5. Per-ticket AI assistance (`POST /api/v1/complaints/{id}/analyze`) and optional Admin AI Insights (`GET /api/v1/dashboard/insights`, `POST /api/v1/dashboard/insights/report`) explicitly display `source: rules` vs `source: local_model`, show no fabricated confidence percentages, and never mutate ticket state without human confirmation (`PATCH /api/v1/complaints/{id}` for classification and `PATCH /api/v1/complaints/{id}/assign` for department/staff assignment).

## Implemented in `frontend/`

- `frontend/FIGMA_WIREFRAME.md` and `frontend/public/wireframe.svg`: Figma wireframe and screen layout specification.
- `frontend/src/api.js`: Single `/api/v1` API client using `sessionStorage` bearer token, 401 session expiry handling, error detail formatting, and authorized binary image fetch.
- `frontend/src/App.jsx`: Login, role-aware tabs (`Report Issue`, `My Complaints`, `Department Queue`, `Admin Dashboard`, `Figma Wireframe`), `/app?embed=1` compact mode, and `/demo-portal` fictional college portal iframe host.
- `frontend/src/components/TicketWorkspace.jsx`: Ticket detail, reporter edit while `SUBMITTED`, JPEG/PNG upload (`<= 5 MiB`) + retry flow, per-ticket AI triage panel (`ADMIN`/`COORDINATOR`), classification update (`PATCH /api/v1/complaints/{id}`), department/staff assignment (`PATCH /api/v1/complaints/{id}/assign`, `GET /api/v1/staff?department_id=...`), workflow status transitions (`PATCH /api/v1/complaints/{id}/status`) with staff verification checkbox and required outcome notes, reporter feedback CRUD (`1–5` rating on `RESOLVED` tickets), and chronological history timeline.
- `frontend/src/components/AdminDashboard.jsx`: Single Admin Dashboard with Operational Inbox, Resolution Analytics (`GET /api/v1/dashboard/stats` with `null` average handling), Optional AI Insights cohort view & on-demand report, and `ADMIN` category/department configuration CRUD.

## Full Windows Integration Verification (`feature/frontend` + `origin/feature/backend` + `origin/feature/ai`)

> **Correction note**: An earlier draft of this section contained inaccurate narrative text (`DEMO-2026-000001`, a nonexistent confidence percentage, `PATCH /complaints/1/classification`, and `POST /complaints/1/assign`) that did not match the actual committed code or the captured screenshots. The section below records the exact commit references, startup commands, Uvicorn HTTP trace, and sanitized browser/API outputs observed from the explicit combined checkout on 2026-10-24.

### 1. Exact Commit References & Checkout Commands

```powershell
git worktree add --detach work/integration origin/feature/backend
git -C work/integration merge --no-edit origin/feature/ai
git -C work/integration merge --no-edit feature/frontend
git -C work/integration rev-parse HEAD origin/feature/backend origin/feature/ai feature/frontend
```

- `origin/feature/backend`: `203eb7f1a6f06a8b24a3f01d9914d1ef3c57ac0e` (`203eb7f`)
- `origin/feature/ai`: `a8300045fb3e2d64cf2201d919438134fd3326c6` (`a830004`)
- `feature/frontend`: `7613e19fedf2c1e690fa087ef8cf3f22930b36c4` (`7613e19`)
- Combined temporary integration merge HEAD (`work/integration`): `284702d0602e987634430ca9996e5a409ed8b507` (`284702d`, zero merge conflicts)

### 2. Automated Test Suites & Startup Commands

1. **AI unit test suite & backend adapter check**:
   ```powershell
   D:\cr_temp\venv\Scripts\python.exe -m unittest discover -s work/integration/tests/ai -v
   D:\cr_temp\venv\Scripts\python.exe work/integration/tests/ai/check_backend_adapter.py work/integration/backend
   ```
   - Result: **Ran 22 tests in 0.042s — OK**; `check_backend_adapter.py` passed.

2. **Backend + AI live PostgreSQL pytest suite**:
   ```powershell
   $env:DATABASE_URL="postgresql://campusresolve:campusresolve_local@127.0.0.1:5432/campusresolve"
   $env:TEST_DATABASE_URL="postgresql://campusresolve:campusresolve_local@127.0.0.1:5432/campusresolve_test"
   Set-Location work\integration\backend
   D:\cr_temp\venv\Scripts\python.exe -m pytest -v
   ```
   - Result: **17 passed, 1 warning in 9.85s** (`tests/test_ai_integration.py`: 9 passed; `tests/test_api.py`: 8 passed).

3. **Frontend production build & contract test**:
   ```powershell
   npm --prefix frontend run build
   npm --prefix frontend test
   ```
   - Result: `vite v6.4.5 building for production... ✓ 30 modules transformed. ✓ built in 748ms`; `Frontend verification passed: 17 endpoint groups, v0.2 contract alignment, and production dist/ bundle verified.`

4. **Explicit service startup commands**:
   ```powershell
   # 1. PostgreSQL 18.4 on 127.0.0.1:5432
   & "D:\cr_temp\pg-env\Library\bin\postgres.exe" -D "D:\cr_temp\pgdata" -p 5432 -h 127.0.0.1

   # 2. FastAPI + AI backend on 127.0.0.1:8000
   $env:DATABASE_URL="postgresql://campusresolve:campusresolve_local@127.0.0.1:5432/campusresolve"
   $env:AUTH_SECRET="local-integration-secret-key-2026-campusresolve"
   Set-Location work\integration\backend
   & "D:\cr_temp\venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000

   # 3. Vite React frontend dev server on 127.0.0.1:5173 (proxying /api -> http://127.0.0.1:8000)
   Set-Location work\integration\frontend
   npm run dev -- --host 127.0.0.1 --port 5173 --strictPort

   # 4. Headless Chrome E2E verification
   & "D:\cr_temp\pg-env\Library\bin\psql.exe" -h 127.0.0.1 -U postgres -d campusresolve -c "TRUNCATE complaints, complaint_status_history, assignments, feedback RESTART IDENTITY CASCADE;"
   node work/run_ui_e2e.mjs
   ```

### 3. Observed Browser Workflow Results

1. **Submit complaint with image**:
   - Signed in as `student@demo.edu` (`Student 1` quick-fill -> `POST /api/v1/auth/login`).
   - Submitted Complaint #1 with title `"Wi-Fi router offline in Block B Lab 204"`, location `"Block B / Lab 204"` (from `GET /api/v1/locations`), category `-- Uncategorized / Not Sure (Admin Review) --` (`category_id: null`), description `"The wireless access point in Lab 204 disconnects students every few minutes during lab session."`, and a 64x64 PNG file (`POST /api/v1/complaints` -> `201 Created`, followed by `POST /api/v1/complaints/1/image` -> `200 OK`).
   - Created ticket record in PostgreSQL: `ticket_number: "CMP-000001"`, `category_id: null`, `assigned_department_id: null`, `priority: "NORMAL"`, `status: "SUBMITTED"`, `image_url: "/api/v1/complaints/1/image"`.
   - The evidence image rendered in `<img src="blob:http://127.0.0.1:5173/...">` via authenticated `GET /api/v1/complaints/1/image`.
   - Submitted Complaint #2 (`CMP-000002`, title `"Overflowing waste bins in Cafeteria"`, location `"Cafeteria"`, category `"Cleanliness"` (`id: 5`), automatically routed by category rule to `"Housekeeping"` (`assigned_department_id: 3`)).

2. **Student accounts cannot access admin AI features**:
   - Confirmed in the browser DOM that `button:has-text("Admin Dashboard")` count is `0` for `STUDENT`.
   - Confirmed via `fetch` with the student's Bearer token that all 4 admin/coordinator endpoints return `403 Forbidden` with `{"detail": "Your role cannot perform this action"}`:
     - `POST /api/v1/complaints/1/analyze` -> `403`
     - `GET /api/v1/dashboard/insights?from=2026-10-24&to=2026-10-24` -> `403`
     - `POST /api/v1/dashboard/insights/report` -> `403`
     - `GET /api/v1/dashboard/stats` -> `403`

3. **AI suggestions appear without automatically changing the ticket**:
   - Signed in as `admin@demo.edu`, selected `CMP-000001`, and clicked **Get AI Suggestions** (`POST /api/v1/complaints/1/analyze` -> `200 OK`).
   - Observed AI Triage panel text (no confidence percentage):
     - Badge: `source: rules (Rules-based local fallback)`
     - `Suggested Priority: NORMAL`
     - `Summary: Wi-Fi router offline in Block B Lab 204`
     - `Reasoning: Keyword rules matched the configured category 'Wi-Fi / Network'. Department suggestion follows its configured routing rule.`
     - `Suggested Category: Wi-Fi / Network • Suggested Department: IT`
     - `Suggested Next Steps for Staff`:
       - `Test connectivity at the reported location and review network service logs before deciding on a repair.`
       - `An authorized person should verify the suggested handling and confirm the work before resolution.`
   - Verified via `GET /api/v1/complaints/1` and `GET /api/v1/complaints/1/history` before and after `POST /api/v1/complaints/1/analyze` that `category_id` remained `null`, `assigned_department_id` remained `null`, and `history.length` remained `1`.

4. **Human confirmation, Assign -> In Progress -> Resolved -> Feedback**:
   - Clicked **Confirm & Apply Category/Priority** (`PATCH /api/v1/complaints/1` with `{"priority": "NORMAL", "category_id": 1}`), which updated `category_id` to `1` (`Wi-Fi / Network`) and applied rule-based routing to department `1` (`IT`, recording history entry `Assignment: IT (Department Queue)` with note `"Category changed; routing reapplied"`).
   - Selected `IT Staff (Staff #3)` in **Named Staff Assignee** and clicked **Save Department Assignment** (`PATCH /api/v1/complaints/1/assign` with `{"department_id": 1, "assigned_user_id": 3}`), recording history entry `Assignment: IT (Staff #3)`.
   - Signed in as `it.staff@demo.edu` (`IT Staff`, `id: 3`), opened `CMP-000001` in **Department Queue**, entered progress note `"Investigating Lab 204 access point and switch port."`, and clicked **Mark as IN_PROGRESS** (`PATCH /api/v1/complaints/1/status` -> `200 OK`).
   - Entered outcome note `"Replaced faulty PoE injector in Block B Lab 204 and verified stable Wi-Fi signal."`, checked the staff verification checkbox, and clicked **Mark as RESOLVED** (`PATCH /api/v1/complaints/1/status` -> `200 OK`), bringing the Audit History Timeline to 5 entries.
   - Signed in as `student@demo.edu`, opened `CMP-000001`, and submitted `5 Stars — Excellent resolution` feedback with comment `"Wi-Fi is fast and stable in Lab 204 now, thank you!"` (`POST /api/v1/complaints/1/feedback` -> `201 Created`).

5. **Analytics update correctly**:
   - Signed in as `admin@demo.edu` and opened **2. Resolution Analytics** (`GET /api/v1/dashboard/stats` -> `200 OK`).
   - Observed `statsData`: `total: 2`, `submitted: 1`, `in_progress: 0`, `resolved: 1`, `rejected: 0`, `resolved_count: 1`, `avg_resolution_hours: 0` (displayed as `0.00h`), `by_category: [{"category_id": 5, "category": "Cleanliness", "count": 1}, {"category_id": 1, "category": "Wi-Fi / Network", "count": 1}]`.

6. **AI Insights displays accurate counts, locations, and recommendations**:
   - Opened **3. AI Insights (Optional Tab)** (`GET /api/v1/dashboard/insights?from=2026-09-24&to=2026-10-24` -> `200 OK`) and clicked **Generate Recommendations Report** (`POST /api/v1/dashboard/insights/report` -> `200 OK`).
   - Observed cohort figures: `sample_size: 2`, `unresolved: 1`, `high_priority_unresolved: 0`, `resolved_count: 1`, `avg_resolution_hours: 0`, location hotspots `Block B / Lab 204 — Wi-Fi / Network (1)` and `Cafeteria — Cleanliness (1)`, oldest unresolved backlog `CMP-000002 • Cafeteria • Age: 0.0h`.
   - Observed generated report (`source: "rules"`):
     - Executive Summary: `"2 reported tickets in the selected creation-date cohort; 1 currently unresolved, including 0 high-priority reports. Among categorized issues, Cleanliness accounts for 1 of 2 tickets. Block B / Lab 204 has 1 reported ticket. Counts measure reports, not unique affected people. Mean resolution time is 0.00 hours across 1 resolved ticket."`
     - 3 Evidence-Based Recommendations: `"Review the Cleanliness report"` (`ASSESSMENT`), `"Inspect reported issues at Block B / Lab 204"` (`ASSESSMENT`), and `"Review the unresolved queue"` (`IMMEDIATE`).

### 4. Sanitized Browser E2E Output & Backend HTTP Trace

```json
{
  "ok": true,
  "observed": {
    "createdTicket": {
      "id": 1,
      "ticket_number": "CMP-000001",
      "reporter_user_id": 1,
      "title": "Wi-Fi router offline in Block B Lab 204",
      "description": "The wireless access point in Lab 204 disconnects students every few minutes during lab session.",
      "location": "Block B / Lab 204",
      "category_id": null,
      "status": "SUBMITTED",
      "priority": "NORMAL",
      "assigned_department_id": null,
      "assigned_user_id": null,
      "image_url": "/api/v1/complaints/1/image",
      "resolved_at": null
    },
    "studentForbiddenCheck": {
      "analyzeStatus": 403,
      "analyzeBody": { "detail": "Your role cannot perform this action" },
      "insightsStatus": 403,
      "insightsBody": { "detail": "Your role cannot perform this action" },
      "reportStatus": 403,
      "reportBody": { "detail": "Your role cannot perform this action" },
      "statsStatus": 403,
      "statsBody": { "detail": "Your role cannot perform this action" }
    },
    "aiAnalyzeNoMutation": {
      "beforeCategoryId": null,
      "afterCategoryId": null,
      "beforeAssignedDepartmentId": null,
      "afterAssignedDepartmentId": null,
      "beforeHistoryLen": 1,
      "afterHistoryLen": 1
    },
    "savedFeedback": {
      "id": 1,
      "complaint_id": 1,
      "author_user_id": 1,
      "rating": 5,
      "comment": "Wi-Fi is fast and stable in Lab 204 now, thank you!"
    },
    "statsData": {
      "total": 2,
      "submitted": 1,
      "in_progress": 0,
      "resolved": 1,
      "rejected": 0,
      "resolved_count": 1,
      "avg_resolution_hours": 0,
      "by_category": [
        { "category_id": 5, "category": "Cleanliness", "count": 1 },
        { "category_id": 1, "category": "Wi-Fi / Network", "count": 1 }
      ]
    }
  }
}
```

Observed Uvicorn HTTP trace during the browser run:
```text
POST /api/v1/auth/login HTTP/1.1" 200 OK
POST /api/v1/complaints HTTP/1.1" 201 Created
POST /api/v1/complaints/1/image HTTP/1.1" 200 OK
GET  /api/v1/complaints/1/image HTTP/1.1" 200 OK
POST /api/v1/complaints HTTP/1.1" 201 Created
POST /api/v1/complaints/1/analyze HTTP/1.1" 403 Forbidden
GET  /api/v1/dashboard/insights?from=2026-10-24&to=2026-10-24 HTTP/1.1" 403 Forbidden
POST /api/v1/dashboard/insights/report HTTP/1.1" 403 Forbidden
GET  /api/v1/dashboard/stats HTTP/1.1" 403 Forbidden
POST /api/v1/auth/login HTTP/1.1" 200 OK
POST /api/v1/complaints/1/analyze HTTP/1.1" 200 OK
PATCH /api/v1/complaints/1 HTTP/1.1" 200 OK
GET  /api/v1/staff?department_id=1 HTTP/1.1" 200 OK
PATCH /api/v1/complaints/1/assign HTTP/1.1" 200 OK
POST /api/v1/auth/login HTTP/1.1" 200 OK
PATCH /api/v1/complaints/1/status HTTP/1.1" 200 OK
PATCH /api/v1/complaints/1/status HTTP/1.1" 200 OK
POST /api/v1/auth/login HTTP/1.1" 200 OK
POST /api/v1/complaints/1/feedback HTTP/1.1" 201 Created
POST /api/v1/auth/login HTTP/1.1" 200 OK
GET  /api/v1/dashboard/stats HTTP/1.1" 200 OK
GET  /api/v1/dashboard/insights?from=2026-09-24&to=2026-10-24 HTTP/1.1" 200 OK
POST /api/v1/dashboard/insights/report HTTP/1.1" 200 OK
```

### 5. Recorded Screenshots (`frontend/screenshots/`)

1. [`frontend/screenshots/01_student_submitted_with_image.png`](../../frontend/screenshots/01_student_submitted_with_image.png) — Student submitted `CMP-000001` (`Wi-Fi router offline in Block B Lab 204`) with authenticated `Blob` PNG preview and `Edit Report` button while `SUBMITTED`.
2. [`frontend/screenshots/02_admin_ai_suggestions_no_mutation.png`](../../frontend/screenshots/02_admin_ai_suggestions_no_mutation.png) — Admin clicked `Get AI Suggestions` (`source: rules`, `Suggested Category: Wi-Fi / Network`, `Suggested Department: IT`, `Suggested Priority: NORMAL`, no confidence percentage) while ticket header still shows `Category: Uncategorized (Needs Review)` and `Assigned Department: Unassigned`.
3. [`frontend/screenshots/03_admin_assigned_it_staff.png`](../../frontend/screenshots/03_admin_assigned_it_staff.png) — Admin clicked `Confirm & Apply Category/Priority` (`PATCH /api/v1/complaints/1`) and assigned `IT` + `IT Staff (Staff #3)` (`PATCH /api/v1/complaints/1/assign`), showing 3 entries in the Audit History Timeline.
4. [`frontend/screenshots/04_staff_resolved_with_history.png`](../../frontend/screenshots/04_staff_resolved_with_history.png) — IT Staff (`it.staff@demo.edu`) moved `CMP-000001` `SUBMITTED -> IN_PROGRESS -> RESOLVED` (`PATCH /api/v1/complaints/1/status`) with staff verification and outcome note, showing all 5 entries in the Audit History Timeline.
5. [`frontend/screenshots/05_student_feedback_submitted.png`](../../frontend/screenshots/05_student_feedback_submitted.png) — Student reporter submitted `5/5 Stars` feedback (`POST /api/v1/complaints/1/feedback`) on resolved `CMP-000001`.
6. [`frontend/screenshots/06_admin_resolution_analytics.png`](../../frontend/screenshots/06_admin_resolution_analytics.png) — Admin `2. Resolution Analytics` tab showing `2` Total Active Reports, `1` Submitted, `1` Resolved, `0.00h` Mean Resolution Time, and Category breakdown (`Cleanliness: 1`, `Wi-Fi / Network: 1`).
7. [`frontend/screenshots/07_admin_ai_insights_and_report.png`](../../frontend/screenshots/07_admin_ai_insights_and_report.png) — Admin `3. AI Insights (Optional Tab)` showing cohort counts (`2` sample size, `1` unresolved), location hotspots (`Block B / Lab 204`, `Cafeteria`), backlog (`CMP-000002`), and on-demand `source: rules` recommendations report.

### 6. Remaining Issues / Pending Items

- **None blocking P0 or P1**: All 6 required browser checks pass end-to-end against `origin/feature/backend` (`203eb7f`) and `origin/feature/ai` (`a830004`).
- **Pending final branch merges to `main`**: Each branch (`feature/backend`, `feature/ai`, `feature/frontend`) remains on its own feature PR for Rohan's integration review before merging to `main`.
