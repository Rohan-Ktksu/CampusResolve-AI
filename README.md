# CampusResolve AI

Campus issue reporting and resolution hackathon project led by **Rohan Sai (@Rohan-Ktksu)**, with **Atif (@Atif-Ur-Rehman)** on backend and **Sonia (@sonia449-prog)** on frontend. SunoSetu is a suggested future name; no rename decision is assumed.

Working prototype. Students and staff report campus issues with an optional photo and get a ticket number (`CMP-000042`). Admins and coordinators route tickets to departments. Department staff move them through Submitted → In Progress → Resolved/Rejected. Reporters rate the outcome, and the admin dashboard shows real resolution-time analytics. Rules-based assistance suggests a category, department, priority and next steps for each ticket, and an optional AI Insights tab produces evidence-based reports. All suggestions are labelled `source: rules`; no language model is used.

## Live demo (temporary)

- App: https://literacy-saturn-done-licence.trycloudflare.com/app
- Fictional college portal with the embedded app: https://literacy-saturn-done-licence.trycloudflare.com/demo-portal

This is a free Cloudflare quick tunnel to Sonia's local machine. It works only while her PostgreSQL, backend, frontend and `cloudflared` processes are running. The address changes whenever the tunnel restarts, so update this section when that happens. Log in with the demo accounts below, and use synthetic data only.

## Quick start (local, free)

Requires Python 3.12+, Node.js/npm and a local PostgreSQL 14+.

1. **Database.** Create user `campusresolve` with databases `campusresolve` and `campusresolve_test`. Exact Windows (`psql`) and podman/docker commands are in [backend/README.md](backend/README.md).
2. **Config.** Copy `.env.example` to `.env` and set `DATABASE_URL` and a random `AUTH_SECRET`. Never commit `.env`.
3. **Backend** (http://127.0.0.1:8000, docs at `/docs`). Tables and demo data are created on first start:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
   pip install -r backend/requirements.txt
   cd backend
   uvicorn app.main:app --port 8000
   ```

4. **Frontend** (http://127.0.0.1:5173; the dev server proxies `/api` to the backend):

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   The embedded view is at `/app?embed=1`, and a fictional college portal wrapper at `/demo-portal`.

## Demo accounts

Fictional institution `DEMO`, password `demo1234` for every account (local prototype only):

| Email | Role |
|---|---|
| student@demo.edu, student2@demo.edu | Student |
| it.staff@demo.edu | Staff, IT |
| facilities.staff@demo.edu | Staff, Facilities |
| coordinator@demo.edu | Coordinator |
| admin@demo.edu | Admin |

Seeded departments: IT, Facilities, Housekeeping, Academics, Transport. Categories route to their configured department; tickets without a category go to admin review.

## Tests

```powershell
python scripts/check_contract.py                 # API contract sanity check
python -m unittest discover -s tests/ai          # rules-based assistance
cd backend; python -m pytest -q                  # API + AI integration against campusresolve_test (wiped each run)
cd frontend; npm run build; node test_frontend_contract.mjs
```

Recorded results, environments and known gaps for each area are in `docs/coordination/` (`backend.md`, `frontend.md`, `ai.md`). Screenshots of the end-to-end demo are in `frontend/screenshots/`.

## Team

| Person | Area | Scope |
|---|---|---|
| Atif | `backend/` (except `backend/app/ai/`) | FastAPI/PostgreSQL, auth, CRUD, images, assignments, history, analytics and AI route wiring |
| Sonia | `frontend/` | Figma, React JavaScript/CSS, one admin dashboard and optional AI Insights tab |
| Rohan | `backend/app/ai/`, `tests/ai/` | In-process ticket suggestions and admin-report functions; integration |

All three feature branches are merged into `main`. Further changes use short-lived branches and PRs reviewed by Rohan. Contributor rules are in [AGENTS.md](AGENTS.md).

## No-spend baseline

No paid inference, hosting, cloud database, automated AI workflow, or new subscription is required. Everything runs locally on PostgreSQL with explicitly labelled rules-based suggestions. Existing coding-assistant plan limits still apply. No billing or overage is enabled by these files.

## Main documents

- [docs/PROJECT_MASTER_PLAN.md](docs/PROJECT_MASTER_PLAN.md): agreed product and demo scope.
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) and [docs/openapi.json](docs/openapi.json): API contract v0.2, frozen (SHA-256 `d32af66a…`, accepted by backend and frontend).
- [backend/app/ai/README.md](backend/app/ai/README.md): assistance function interfaces and fallback rules.
- [docs/coordination/README.md](docs/coordination/README.md): how contract changes are proposed and accepted through Git.
- [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md): repository publishing and teammate start instructions.

## Limitations

Prototype for a hackathon demo: one fictional institution, seeded logins with no SSO or self-registration, and keyword rules rather than a trained model. Tokens are kept in browser sessionStorage. Not production-hardened.

## Attribution

Repository ownership and baseline setup belong to Rohan's verified Git identity. Atif and Sonia retain authorship of their work. No official college affiliation or completed ERP/SSO integration is claimed.
