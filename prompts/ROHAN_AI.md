# Rohan's Codex task

Read AGENTS.md, backend/app/ai/README.md, docs/API_CONTRACT.md, and coordination files. Work on feature/ai. Own backend/app/ai/, tests/ai/, and docs/coordination/ai.md. Keep module imports independent of the FastAPI/database implementation.

Implement dependency-free, clearly labeled rules-based ticket assistance first. Inputs are permitted category/department IDs and text; outputs use only those IDs with a reason, suggested next steps, and needs_review. Unknown or ambiguous text must not force an assignment. Atif owns route wiring.

Next provide an optional admin report function over server-calculated aggregate counts. Identify frequent issues, location hotspots, urgent backlog, and practical improvements with supporting figures. Do not invent costs, causes, or numerical benefits. No paid model APIs or cloud services. A future local model must use the same output contract and honest source labeling.

Verify output constraints and failure/no-data cases with synthetic examples. Help integrate accepted contracts and the end-to-end demo. Never overwrite Sonia/Atif implementation or attribute their commits to Rohan.
