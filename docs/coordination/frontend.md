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

## Next

- Complete `npm run build` verification and connect live frontend submission to Atif's PostgreSQL backend to verify end-to-end `submit -> assign -> update status -> resolve -> feedback -> analytics`.
