# Windows and GitHub handoff

Owner: Rohan Sai / Rohan-Ktksu. Collaborators: Atif-Ur-Rehman (backend), sonia449-prog (frontend). Use their own accounts; do not share tokens or paid subscriptions.

## Publish under Rohan's account

These commands describe the intended setup; check current state before repeating a step. A repository might already have been published by the setup assistant. Never overwrite an existing unrelated repository.

```powershell
gh auth status
git status --short --branch
git remote -v
```

If authentication expired, Rohan completes `gh auth login --hostname github.com --git-protocol https --web` in his own browser. Do not put a personal access token in chat or a Git URL.

From a clean baseline commit on main with no remote, the agreed publication is:

```powershell
gh repo create Rohan-Ktksu/CampusResolve-AI --private --source . --remote origin --push --description "Campus issue resolution hackathon project by Rohan, Atif and Sonia"
git push origin feature/backend feature/frontend feature/ai
gh api --method PUT repos/Rohan-Ktksu/CampusResolve-AI/collaborators/Atif-Ur-Rehman -f permission=push
gh api --method PUT repos/Rohan-Ktksu/CampusResolve-AI/collaborators/sonia449-prog -f permission=push
```

Both friends must accept invitations; a sent invitation does not mean accepted access. No Actions workflow, cloud deployment, paid inference, billing enrollment, or new subscription is configured.

## Each friend's computer

1. Accept the GitHub repository invitation using the intended account.
2. Install/verify Git. Atif verifies Python and local PostgreSQL; Sonia verifies Node/npm. No paid plugin is required for file-based coordination.
3. Clone `https://github.com/Rohan-Ktksu/CampusResolve-AI.git` and open the cloned folder in the coding assistant.
4. Verify `git config user.name`, `git config user.email`, and authenticated account. Use your own verified identity, not Rohan's.
5. Atif checks out feature/backend; Sonia feature/frontend. Existing remote branches should be tracked, not recreated from an old unrelated state.
6. Paste prompts/ATIF_BACKEND.md into Claude Code or prompts/SONIA_FRONTEND.md into Antigravity. Explicitly ask the assistant to read AGENTS.md and its entry-point file before implementation.
7. Follow docs/coordination/README.md to propose/review the API through ordinary commits. Do not expect the other assistant to wake automatically.

Claude entry point: CLAUDE.md imports AGENTS.md. Antigravity entry point: GEMINI.md directs the assistant to the same shared rules. These match the official instruction mechanisms; no custom agent API service is installed.

## Rohan's Python environment

The local .venv is ignored and is not sent to friends. Each developer creates their own environment. Python 3.12 is available on Rohan's checked computer. Do not commit .env or real credentials.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python scripts/check_contract.py
```

If Windows blocks activation, use `.\.venv\Scripts\python.exe` directly; do not weaken machine-wide execution policy. If a sandbox temp directory prevents pip bootstrapping, use a writable temporary folder in work/ for that process; no system permission change is needed. Atif supplies actual requirements and startup instructions after backend implementation. There is no runnable FastAPI app in this baseline.

## Cost and connection expectations

GitHub Free permits collaborators on public/private repositories. Coding-assistant plan usage still has limits. The project baseline uses local PostgreSQL and rules-based application assistance, not paid model inference. Avoid enabling paid overage/credits or any metered runner. A future local model is optional and depends on hardware; do not promise unlimited hosted AI for free.

Choose one integration laptop. `localhost` always means the current computer. Sonia either runs the backend locally or uses an explicitly reachable development server. The final same-origin demo serves the built frontend and /api/v1 together. Hosted deployment is not required.

Sources checked 24 October 2026:

- [GitHub repository creation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
- [GitHub Free collaborators](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)
- [Claude shared instruction import](https://code.claude.com/docs/en/memory)
- [Antigravity workspace rules](https://antigravity.google/docs/rules/)
