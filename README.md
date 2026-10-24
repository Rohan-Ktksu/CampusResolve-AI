# CampusResolve AI

Campus issue reporting and resolution hackathon project led by **Rohan Sai (@Rohan-Ktksu)**, with **Atif (@Atif-Ur-Rehman)** on backend and **Sonia (@sonia449-prog)** on frontend.

This repository starts as a team handoff and contract baseline, not a completed application. SunoSetu is a suggested future name; no rename decision is assumed.

## Start here

1. All assistants read AGENTS.md. Atif starts with prompts/ATIF_BACKEND.md; Sonia with prompts/SONIA_FRONTEND.md; Rohan with prompts/ROHAN_AI.md.
2. Atif proposes the canonical API; Sonia independently accepts or requests changes through Git-tracked coordination files. See docs/coordination/README.md. No paid agent communication service is needed.
3. Complete the database-backed issue lifecycle before optional AI Insights or embedding.

## Team

| Person | Branch | Scope |
|---|---|---|
| Atif | feature/backend | FastAPI/PostgreSQL, auth, CRUD, images, assignments, history, analytics and AI route wiring |
| Sonia | feature/frontend | Figma, React JavaScript/CSS, one admin dashboard and optional AI Insights tab |
| Rohan | feature/ai | In-process ticket suggestions and admin-report functions; integration |

## No-spend baseline

No paid inference, hosting, cloud database, automated AI workflow, or new subscription is required by this setup. Run locally, use local PostgreSQL, and use explicitly labeled rules-based suggestions until a local model is deliberately chosen. Existing coding-assistant plan limits still apply; this setup cannot make their usage unlimited. No billing or overage is enabled by these files.

## Local preparation

Python 3.12 and Node/npm are available on Rohan's checked computer. Use `python`, not the broken `py` discovery on that machine. Atif installs/configures local PostgreSQL and documents reproducible backend dependencies/run commands as part of his implementation. Sonia creates the React frontend and documents its build command. No dependencies are installed in this baseline.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python scripts/check_contract.py
```

Replace local database/password/secret placeholders; do not commit .env. These are preparation commands, not an app startup command. The source code skeleton has not yet implemented the application.

Each teammate clones the SAME repository after Rohan publishes it, verifies their own Git identity, and creates/checks out their assigned branch. If GitHub authentication is unavailable, use a local handoff ZIP temporarily; Git-based cross-PC contract exchange begins only after access is restored.

## Main documents

- docs/PROJECT_MASTER_PLAN.md — agreed product and demo scope.
- docs/API_CONTRACT.md and docs/openapi.json — proposed wire contract.
- backend/app/ai/README.md — callable interfaces and free fallback rules.
- docs/coordination/README.md — independent assistant negotiation.
- docs/WINDOWS_SETUP.md — repository publishing and teammate start instructions.

## Attribution

Repository ownership and baseline setup belong to Rohan's verified Git identity. Atif and Sonia retain authorship of their work. No official college affiliation or completed ERP/SSO integration is claimed.
