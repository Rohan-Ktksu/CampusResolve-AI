# Atif / backend

State: PROPOSED
Contract SHA-256 (docs/openapi.json, LF): d32af66a4cab39db4c5e56f7dd5e4f34ff70b10a21cac714eb6d756f5225b62c
Contract version: 0.2.0
Branch: feature/backend

## Proposal summary for Sonia

No endpoint or schema shape changed from the seed v0.1. v0.2 only fixes routine semantics, listed at the top of docs/API_CONTRACT.md: ticket format `CMP-000042`, `image_url` value, location must come from `GET /locations`, list ordering, token lifetime, seeded demo accounts, and the rules-only analyze fallback.

Review with:

```
git fetch origin
git show origin/feature/backend:docs/openapi.json > work/openapi.json
python scripts/check_contract.py
Get-FileHash work/openapi.json -Algorithm SHA256
```

Record ACCEPTED plus the identical hash in docs/coordination/frontend.md, or numbered CHANGES_REQUESTED with JSON examples.

Review responses: none yet.
Tests actually run by Atif: `python scripts/check_contract.py` → "Contract sanity check passed: 31 operations".

Next: implement login and persisted complaint create/list, then assign → status → resolve → feedback → stats.
