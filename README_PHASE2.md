# SolarAI Phase 2 — hybrid assistant package

This is an additive code package for the existing Phase 1 repository.
It does not contain the full existing repository or deploy anything.

1. In your existing repository, ensure a clean `git status`, then create branch `feature/phase-2-ai-assistant`.
2. Copy the included `backend/` and `frontend/` directories into the repository, retaining existing files.
3. Copy `apply_phase2.py` to the repository root and run `python apply_phase2.py`.
4. From `backend/`, run `pytest -q`. From `frontend/`, run `npm install && npm run build`.
5. Test POST `/ai-assistant/ask` using your existing JWT token, e.g. `{"question":"battery undervoltage"}`.
6. Confirm Phase 1 dashboard, login, alerts, telemetry, and diagnostics still work.
7. Only deploy after staging validation.

Optional server-only environment variables:
`SOLARAI_AI_ENABLED=true`
`SOLARAI_LLM_API_KEY=<private secret>`
`SOLARAI_LLM_MODEL=gpt-4.1-mini`
`SOLARAI_LLM_BASE_URL=https://api.openai.com/v1`

Default: AI disabled, deterministic fallback works without an external key.
No database migration or new frontend package is required.
The knowledge base is generic guidance, NOT verified manufacturer documentation.
The current ML classifier is a synthetic-data prototype.
Further work for production: per-user rate limiting, provider cost controls, request audit logging,
manufacturer manual licensing/provenance, telemetry validation, and field testing.
