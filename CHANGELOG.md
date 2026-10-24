# Changelog

Every version of CampusResolve AI, newest first. Each entry says what changed, who changed it, the PR, and where it runs.

- **Versions:** each released version gets a Git tag (`v0.3.0`, …) on the `main` commit that shipped it.
- **Contract versions:** the API contract has its own version and SHA-256, recorded in [`docs/coordination/`](docs/coordination/).

## v0.4.0 — Free cloud deployment (Vercel + Neon) · 2026-10-24

PRs [#7](https://github.com/Rohan-Ktksu/CampusResolve-AI/pull/7) (merge `26f7db1`) and the follow-up build fix · by Rohan

- **Hosting:** the app runs on **Vercel** (free Hobby plan), with no laptop needed. React is served as static files, and FastAPI runs as a Python function at `api/index.py`, in the Singapore region.
- **Database:** **Neon** free PostgreSQL 16 in Singapore. Tables and demo accounts are created automatically on first use.
- **Photos in PostgreSQL:** stored in a new `complaint_images` table instead of on disk, because Vercel functions keep no files. Photos already on disk in local databases still work.
- **Upload limit:** configurable with `MAX_UPLOAD_BYTES`. The Vercel deployment uses 4 MiB, to fit Vercel's 4.5 MB request limit; local runs keep 5 MiB.
- **Team rule:** `AGENTS.md` now allows free (no card) Vercel + Neon hosting for the public demo.
- **API contract:** unchanged (v0.3, `d726d73c…`).
- **Startup fix:** concurrent serverless cold starts could both create the tables and collide; table setup now takes a PostgreSQL advisory lock.
- **Build fix:** Vercel cannot read `-r` includes, so the runtime packages now live in the root `requirements.txt`; `backend/requirements.txt` includes it and adds the test tools.

| Infrastructure | Value |
|---|---|
| Vercel project | `campusresolve-ai` (account `rohansai`, Hobby) |
| Vercel production branch | `main` (every merge redeploys automatically) |
| Neon project | `campusresolve` (`bold-sunset-29788383`), AWS Singapore, PostgreSQL 16, Free |
| Settings in Vercel | `DATABASE_URL`, `AUTH_SECRET` (both encrypted), `MAX_UPLOAD_BYTES=4194304` |

## v0.3.0 — NLTK assistant, admin chatbox, common issues · 2026-10-24

PR [#5](https://github.com/Rohan-Ktksu/CampusResolve-AI/pull/5) · merge `b0b4c88` · by Rohan; contract accepted and live-tested by Sonia

- **Ask & Reports chatbox:** English questions become a safe, editable report table with summary, suggestions and CSV export.
- **Common issues:** complaint descriptions are grouped into issues, with times reported, student reporters, open count and suggestions. Shown on the dashboard, in the report and in the chatbox.
- **NLTK analysis:** ticket triage and reports use NLTK stemming, typo tolerance and term frequency (`source: nlp`).
- **8 new categories:** Infrastructure, Food / Canteen, Hostel, Safety / Security, Housekeeping, Library, Academics, Sports.
- **3 new departments:** Food Services, Hostel Office, Campus Security.
- **API contract v0.3** (additive), SHA-256 `d726d73c…`, accepted by frontend.
- **README:** rewritten, with features, the build journey, contributions and the live demo.
- **Protection on `main`:** pull request with 1 approval, no force-push, no deletion.
- **Hosting:** Sonia's Cloudflare quick tunnel (temporary).

## v0.2.0 — Working prototype · 2026-10-24

PRs [#1](https://github.com/Rohan-Ktksu/CampusResolve-AI/pull/1) (Atif), [#2](https://github.com/Rohan-Ktksu/CampusResolve-AI/pull/2) (Rohan), [#3](https://github.com/Rohan-Ktksu/CampusResolve-AI/pull/3) (Sonia), [#4](https://github.com/Rohan-Ktksu/CampusResolve-AI/pull/4) (Atif) · merge `1b4e347`

- **Backend (Atif):** FastAPI + PostgreSQL, 31 API operations covering login and roles, complaints with photos and unique ticket numbers, assignment, status workflow with history, feedback and analytics.
- **Frontend (Sonia):** React screens for every role, the admin dashboard, the AI Insights tab, the embedded view and `/demo-portal`.
- **AI (Rohan):** rules-based ticket suggestions and evidence-backed admin reports, with a validated fallback.
- **API contract v0.2:** SHA-256 `d32af66a…`, proposed by Atif and accepted by Sonia.
- **First live demo:** Cloudflare quick tunnel.

## v0.1.0 — Team handoff · 2026-10-24

Commit `cde640d` · by Rohan

- Master plan from REVA Problem #3, ownership rules (`AGENTS.md`), and the seed API contract and AI contract.
