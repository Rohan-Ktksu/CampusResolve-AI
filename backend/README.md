# Backend (FastAPI + PostgreSQL)

Local only, no paid services. The schema and the fictional seed data are created on first startup.

## 1. PostgreSQL

Any local PostgreSQL 14+ works. Create a user `campusresolve`, a database `campusresolve`, and (for tests) `campusresolve_test`.

- Windows: install PostgreSQL from postgresql.org, then in `psql -U postgres`:
  `CREATE USER campusresolve PASSWORD 'campusresolve_local'; CREATE DATABASE campusresolve OWNER campusresolve; CREATE DATABASE campusresolve_test OWNER campusresolve;`
- Linux/macOS with podman or docker:
  `podman run -d --name campusresolve-pg -e POSTGRES_USER=campusresolve -e POSTGRES_PASSWORD=campusresolve_local -e POSTGRES_DB=campusresolve -p 5432:5432 docker.io/library/postgres:16`
  then `podman exec campusresolve-pg psql -U campusresolve -c "create database campusresolve_test"`.

Copy `.env.example` to `.env` at the repo root and set `DATABASE_URL` and a random `AUTH_SECRET`. Without `.env`, the defaults above are used and tokens reset on every restart.

## 2. Run (from the repo root, then backend/)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

API: http://127.0.0.1:8000/api/v1. Interactive docs: http://127.0.0.1:8000/docs. The frontend dev proxy should forward `/api` to `BACKEND_URL`.

Seed logins (password `demo1234`): student@demo.edu, student2@demo.edu, it.staff@demo.edu, facilities.staff@demo.edu, coordinator@demo.edu, admin@demo.edu.

## 3. Test

```powershell
cd backend
python -m pytest -q
```

Tests wipe and recreate `campusresolve_test` (override with `TEST_DATABASE_URL`). They never touch the main database.

## Layout

- `app/schema.sql`: tables (idempotent). `app/db.py`: connection, password hashing, seed.
- `app/models.py`: request/response models mirroring docs/openapi.json.
- `app/main.py`: all `/api/v1` routes and permission checks.
- `app/ai/`: Rohan's in-process functions. Routes call `analyze_complaint` / `generate_admin_report` when they exist and fall back to labelled `source: "rules"` output otherwise or on any error/invalid output.
