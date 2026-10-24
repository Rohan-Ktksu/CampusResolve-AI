# API agreement through ordinary Git

Contract state starts **SEED / NOT ACCEPTED**. Having contract files does not imply either assistant reviewed them.

Atif is the single canonical API writer. Sonia owns frontend review. Rohan owns AI interfaces. Assistants can settle routine implementation decisions without asking Rohan to relay messages. The root AGENTS.md defines boundaries and no-spend constraints.

1. Atif updates docs/API_CONTRACT.md + docs/openapi.json, validates them, records PROPOSED with the OpenAPI SHA-256 in backend.md, commits and pushes feature/backend.
2. Sonia fetches and inspects Atif's remote contract and backend.md. Record ACCEPTED plus the identical OpenAPI SHA-256 in frontend.md, or CHANGES_REQUESTED with exact field/endpoint examples. Commit/push feature/frontend.
3. Atif fetches Sonia's review file, addresses routine changes, and publishes a new hash if needed. Sonia checks that version. Agreement requires matching hashes and the actual contract file; no silent implied acceptance.
4. Rohan acknowledges the callable interface separately in ai.md. Atif provides routes; Rohan provides functions, with rules fallback.
5. Record test commands/results, blockers, and the next action in your own file. Check peer updates once per work milestone. No continuous polling, background agents, or new paid model calls to exchange messages.

The tools do not share live context automatically. Each friend must start their own assistant against their clone. A committed file becomes visible only after push/fetch. Until a peer resumes, continue independent work using the seed contract and record assumptions; do not claim it is frozen.

Before merging implementation, Rohan integrates accepted contract files and checks the hashes. Before optional features, the full complaint lifecycle must pass. Escalate only genuine product ambiguity, security conflicts, or spending decisions; use the agreed prototype policies for routine questions.
