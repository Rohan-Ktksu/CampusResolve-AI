# Sonia / frontend

State: ACCEPTED
Reviewed contract SHA-256: d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c
Contract version: 0.2.0
Branch: feature/frontend

## Contract review summary (v0.2.0 from `origin/feature/backend`)

- Fetched `origin/feature/backend` (`6c73887`) and inspected `docs/API_CONTRACT.md`, `docs/openapi.json`, and `docs/coordination/backend.md`.
- Verified `origin/feature/backend:docs/openapi.json` SHA-256 is `d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c`.
- **Decision: `ACCEPTED`** (`d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c`).
- Incorporated all v0.2 frontend alignment notes into `frontend/`:
  1. History timeline uses composite React key `` `${h.kind}-${h.id}` `` because status and assignment history entries originate from two tables.
  2. Location fields on both the Report Issue form and Reporter Edit form use a `<select>` dropdown bound to canonical `name` values from `GET /api/v1/locations`.
  3. Login screen includes quick-fill helpers for the seeded `DEMO` accounts (`student@demo.edu`, `student2@demo.edu`, `it.staff@demo.edu`, `facilities.staff@demo.edu`, `coordinator@demo.edu`, `admin@demo.edu`, password `demo1234`) while authenticating via `POST /api/v1/auth/login`.
  4. Image display uses authenticated `GET /api/v1/complaints/{id}/image` with the Bearer token and renders a temporary `Blob` URL (`URL.createObjectURL`), with upload retry preserved if `POST /api/v1/complaints/{id}/image` fails after `POST /api/v1/complaints` succeeds.
  5. Per-ticket AI assistance (`POST /api/v1/complaints/{id}/analyze`) and optional Admin AI Insights (`GET /api/v1/dashboard/insights`, `POST /api/v1/dashboard/insights/report`) explicitly display `source: rules` vs `source: local_model` and never mutate ticket state without human confirmation.

## Implemented in `frontend/`

- `frontend/FIGMA_WIREFRAME.md` and `frontend/public/wireframe.svg`: Figma wireframe and screen layout specification.
- `frontend/src/api.js`: Single `/api/v1` API client using `sessionStorage` bearer token, 401 session expiry handling, error detail formatting, and authorized binary image fetch.
- `frontend/src/App.jsx`: Login, role-aware tabs (`Report Issue`, `My Complaints`, `Department Queue`, `Admin Dashboard`, `Figma Wireframe`), `/app?embed=1` compact mode, and `/demo-portal` fictional college portal iframe host.
- `frontend/src/components/TicketWorkspace.jsx`: Ticket detail, reporter edit while `SUBMITTED`, JPEG/PNG upload (`<= 5 MiB`) + retry flow, per-ticket AI triage panel (`ADMIN`/`COORDINATOR`), department/staff assignment (`GET /api/v1/staff?department_id=...`), workflow status transitions with verification and required outcome notes, reporter feedback CRUD (`1–5` rating on `RESOLVED` tickets), and chronological history timeline.
- `frontend/src/components/AdminDashboard.jsx`: Single Admin Dashboard with Operational Inbox, Resolution Analytics (`GET /api/v1/dashboard/stats` with `null` average handling), Optional AI Insights cohort view & on-demand report, and `ADMIN` category/department configuration CRUD.

## Full Windows Integration Verification (`feature/frontend` + `origin/feature/backend` + `origin/feature/ai`)

Tested in a temporary detached integration checkout (`work/integration`, cleaned up before committing) combining:
- `feature/frontend` (`c5063f8` + two UI polish fixes)
- `origin/feature/backend` (`203eb7f`)
- `origin/feature/ai` (`a830004`)

### Environment & Commands Run (Windows, Python 3.13.12, PostgreSQL 18.4, Node v24.22.1)

1. **Create temporary integration worktree & merge branches cleanly**:
   ```powershell
   git worktree add --detach work/integration origin/feature/backend
   cd work/integration
   git merge --no-edit origin/feature/ai
   git merge --no-edit feature/frontend
   ```
   - Result: Zero merge conflicts across `backend/`, `backend/app/ai/`, `tests/ai/`, `frontend/`, and `docs/`.

2. **AI unit test suite & backend adapter verification**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s work/integration/tests/ai -v
   .\.venv\Scripts\python.exe work/integration/tests/ai/check_backend_adapter.py work/integration/backend
   ```
   - Result: **Ran 22 tests in 0.042s — OK**; `check_backend_adapter.py` passed (`analyze_ticket`, `generate_insights`, `generate_report` signatures & return shapes verified).

3. **Backend + AI live PostgreSQL test suite**:
   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://campusresolve:campusresolve_local@127.0.0.1:5432/campusresolve"
   $env:TEST_DATABASE_URL="postgresql+psycopg://campusresolve:campusresolve_local@127.0.0.1:5432/campusresolve_test"
   cd work/integration/backend
   C:\Users\sonia.DESKTOP-JDQ8MSR\Downloads\NEW_proj\.venv\Scripts\python.exe -m pytest -v
   ```
   - Result: **17 passed, 1 warning in 9.85s** (`tests/test_ai_integration.py`: 9 passed; `tests/test_api.py`: 8 passed).

4. **Runtime OpenAPI contract check**:
   ```powershell
   curl.exe -s http://127.0.0.1:8000/openapi.json -o work/runtime-openapi.json
   .\.venv\Scripts\python.exe work/integration/scripts/check_contract.py work/runtime-openapi.json
   ```
   - Result: **Contract check passed: 31 operations verified.**

5. **Frontend build & static contract test**:
   ```powershell
   npm --prefix frontend run build
   npm --prefix frontend test
   ```
   - Result: `vite v6.4.5 building for production... ✓ 30 modules transformed. ✓ built in 748ms`; `Frontend verification passed: 17 endpoint groups, v0.2 contract alignment, and production dist/ bundle verified.`

6. **Live Browser End-to-End Verification (Headless Chrome via Playwright against Vite `:5173` + FastAPI `:8000` + PostgreSQL `:5432`)**:
   - Verified all 6 required end-to-end checks in a real Chromium browser session:
     1. **Submit complaint with image**: Logged in as `student@demo.edu` (`demo1234`), submitted complaint with `[UNCAT]` (Uncategorized / Let Admin Route), location `Block B - Labs`, description `"Wi-Fi router in Block B lab is completely offline and blinking red since morning, students cannot access exam portal."`, and a valid PNG attachment (`wifi_evidence.png`). Ticket `DEMO-2026-000001` was created in PostgreSQL with `has_image: true`, `category_id: null`, `department_id: null`, and the authenticated image rendered via `Blob` URL (`blob:http://127.0.0.1:5173/...`).
     2. **Student cannot access admin AI features**: Confirmed while logged in as `student@demo.edu` that the `Admin Dashboard` tab and the `AI Triage & Routing Suggestions` panel are absent from the UI, and direct API calls from the browser session returned:
        - `POST /api/v1/complaints/1/analyze` -> `403` (`Role 'STUDENT' is not permitted; required: ADMIN, COORDINATOR`)
        - `GET /api/v1/dashboard/insights` -> `403` (`Role 'STUDENT' is not permitted; required: ADMIN, COORDINATOR`)
        - `POST /api/v1/dashboard/insights/report` -> `403` (`Role 'STUDENT' is not permitted; required: ADMIN, COORDINATOR`)
     3. **AI suggestions appear without automatically changing the ticket**: Logged in as `admin@demo.edu`, opened `DEMO-2026-000001`, and clicked **Generate AI Suggestions**. The panel displayed `source: rules (deterministic fallback — not a trained LLM)`, suggested Category `IT & Network` (`IT`), Priority `HIGH` (`82% confidence`), Department `IT Services` (`IT`), and 3 recommended next steps. Verified via `GET /api/v1/complaints/1` immediately after analysis that `category_id`, `priority`, `department_id`, and `status` in PostgreSQL remained unchanged (`null`, `null`, `null`, `SUBMITTED`) until the admin clicked **Apply Suggested Category & Priority (`IT`, `HIGH`)** (`PATCH /api/v1/complaints/1/classification`) and **Assign Ticket** (`POST /api/v1/complaints/1/assign` to `IT Services` + `Vikram Nair`).
     4. **Assign -> In Progress -> Resolved -> Feedback**:
        - Logged in as `it.staff@demo.edu` (`Vikram Nair`), opened `DEMO-2026-000001` from `Department Queue`, and transitioned `SUBMITTED -> IN_PROGRESS`.
        - Checked `"I have verified the resolution details before marking this ticket Resolved"`, entered outcome note `"Replaced faulty PoE injector in Block B Lab 204 and verified 5GHz SSID connectivity across 30 lab terminals."`, and transitioned `IN_PROGRESS -> RESOLVED`.
        - Logged back in as `student@demo.edu`, opened `DEMO-2026-000001`, and submitted `5 — Very Satisfied` feedback with comment `"Fast fix by IT team, Wi-Fi in Block B lab is working great now!"`.
     5. **Analytics update correctly**: Logged in as `admin@demo.edu`, opened `Admin Dashboard -> Resolution Analytics (P0)` and verified live metrics: Total Active Tickets `1`, Resolved Tickets `1`, Avg Resolution Time (Hours) `0h` (`0.0` hours, non-null), Average Feedback Rating `5 / 5`, plus breakdowns by Status (`RESOLVED: 1`), Category (`IT & Network: 1`), Department (`IT Services: 1`), and Priority (`HIGH: 1`).
     6. **AI Insights displays accurate counts, locations, and recommendations**: Opened `Admin Dashboard -> Optional AI Insights`, verified source badge `source: rules (deterministic fallback)` and cohort framing (`"Counts represent reported tickets in the selected creation-date cohort, not unique affected people."`), Top Categories (`IT & Network: 1`), Hotspot Locations (`Block B - Labs: 1`), High Priority Share (`100.0%`), and generated the on-demand Executive Report (`POST /api/v1/dashboard/insights/report`), verifying the executive summary, key findings, and actionable recommendations (`IT Services`).

### Recorded Screenshots (`frontend/screenshots/`)

1. [`frontend/screenshots/01_student_submitted_with_image.png`](../../frontend/screenshots/01_student_submitted_with_image.png) — Student submitted `DEMO-2026-000001` with authenticated PNG image preview and reporter edit available while `SUBMITTED`.
2. [`frontend/screenshots/02_admin_ai_suggestions_no_mutation.png`](../../frontend/screenshots/02_admin_ai_suggestions_no_mutation.png) — Admin generated `source: rules` AI triage suggestions (`IT & Network`, `HIGH`, `IT Services`) while ticket header badges still show `Category: Uncategorized (Needs Review)` and `Priority: Unset`.
3. [`frontend/screenshots/03_admin_assigned_it_staff.png`](../../frontend/screenshots/03_admin_assigned_it_staff.png) — Admin explicitly applied classification (`IT`, `HIGH`) and assigned `IT Services` / `Vikram Nair`.
4. [`frontend/screenshots/04_staff_resolved_with_history.png`](../../frontend/screenshots/04_staff_resolved_with_history.png) — IT Staff (`it.staff@demo.edu`) moved ticket `SUBMITTED -> IN_PROGRESS -> RESOLVED` with staff verification and outcome note, showing full status & assignment history timeline.
5. [`frontend/screenshots/05_student_feedback_submitted.png`](../../frontend/screenshots/05_student_feedback_submitted.png) — Student reporter submitted `5 / 5` feedback on the resolved ticket.
6. [`frontend/screenshots/06_admin_resolution_analytics.png`](../../frontend/screenshots/06_admin_resolution_analytics.png) — Admin Resolution Analytics (P0) updated with `1` resolved ticket, `0h` average resolution time, and `5 / 5` average rating.
7. [`frontend/screenshots/07_admin_ai_insights_and_report.png`](../../frontend/screenshots/07_admin_ai_insights_and_report.png) — Admin Optional AI Insights tab displaying accurate cohort counts (`IT & Network: 1`), location hotspot (`Block B - Labs: 1`), recommendations, and generated executive report (`source: rules`).

### Frontend Fixes Applied During Integration Testing

1. `frontend/src/App.jsx`: Cleared `reportSuccess` and `reportError` banners inside `handleLogout` so submission confirmation banners from a previous user session do not stay visible after switching accounts.
2. `frontend/src/components/TicketWorkspace.jsx`: Added an effect cancellation guard around `loadFullTicket()` + `fetchComplaintImageUrl()` so rapid ticket or tab switches cannot overwrite state with a stale in-flight response.

## Remaining Issues / Notes

- **None blocking P0 or P1**: All 6 verification items, 17 backend/AI pytest cases, 22 AI unit tests, 31 OpenAPI contract operations, and frontend production builds pass on Windows.
- **Note on local environment**: If running without Docker/Podman on Windows, point `DATABASE_URL` to a local PostgreSQL 16+ instance (`postgresql+psycopg://campusresolve:campusresolve_local@127.0.0.1:5432/campusresolve`) before starting `uvicorn app.main:app --port 8000` and `npm --prefix frontend run dev`.
