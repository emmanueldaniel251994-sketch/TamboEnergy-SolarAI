# SolarAI continuation audit — 13 October 2026

## Verified starting point

Continue from `feature/phase-2-ai-assistant`, commit `4f8d187` (manufacturer knowledge phases 3A–3K). The shared development history reports 154 passing tests; this audit independently reproduced that result. `main` still describes the earlier telemetry MVP and must not be used as the sole source of current development state.

The existing application uses FastAPI, SQLAlchemy, Alembic, and React/Vite. It includes telemetry, devices, alerts, maintenance, analytics, diagnostic conversations, persisted user-owned assistant sessions, manufacturer/model/document/fault-code records, verification, document intake, PDF review, and review decisions/audit.

## Initial changes

- Add the missing `pypdf` runtime dependency used by PDF intake and PDF tests.
- Add `httpx`, required by the API regression tests using FastAPI TestClient.
- Run CI for the active development branch and `codex/**` branches.
- Run CI for PRs targeting the active development branch as well as `main`.
- Include the existing frontend lint command in CI.

These changes preserve existing application behavior and database schema.

## Validation performed

- Backend: `python -m pytest -q` — **154 passed**, 7 deprecation warnings.
- Fresh local SQLite database: `python -m alembic upgrade head` — succeeded through `0c7151855e86`.
- Frontend: `npm ci --ignore-scripts`, `npm run build`, and `npm run lint` — succeeded. The build reports a large JavaScript chunk; lint reports existing React effect warnings.

Tests used a local test secret and temporary SQLite files. No production database or Railway deployment was accessed. PostgreSQL deployment, browser journeys, and native mobile builds were not validated.

## Remaining work identified

| Area | Evidence and next work |
| --- | --- |
| Assistant UI | `frontend/src/pages/AIAssistant.jsx` calls the stateless `/ai-assistant/ask` endpoint. Connect the existing session APIs to conversation history, follow-up messages, and equipment profile editing. |
| Manufacturer UI | Backend routes exist for intake, review, decisions, and verification. Add role-aware administration and equipment knowledge views using these workflows. |
| PDF processing | `inspect_pdf` parses PDFs in the API process. Page/byte/output limits do not isolate parsing CPU or memory usage. Design a restricted worker with time/resource limits before production intake. |
| Review storage | Review decisions are stored in local JSONL. Move review history to transactional, permission-controlled persistent storage with migration and concurrency tests. Preserve the separation between provenance review and manufacturer verification. |
| Production storage | Pending PDFs require `SOLARAI_PENDING_PDF_DIR`. Define durable storage, access controls, backup, and restore procedures before deployment. |
| Documentation | The main README still presents the earlier MVP. Update it when the integrated frontend and manufacturer workflow are validated. |
| Repository hygiene | Tracked backup copies remain under `backend/phase3*_backup_*` and beside application files. Compare them before removing redundant copies. |
| Wider requested scope | Account recovery, service coordination, business workflows, and native mobile support require a dedicated module-level audit and implementation. Their completion is not established by the current 154-test suite. |

## Review and publishing rules

Work on development branches and open a PR for every pushed change set. Do not merge, enable auto-merge, force-push, delete branches, deploy to Railway, or modify production data. The repository owner reviews and merges.

The initial audit was performed with read-only access. After the repository owner accepted the collaborator invitation, the connected GitHub account `baalebos-cloud` was confirmed to have write access. Publish this change set on its own development branch with a PR targeting `feature/phase-2-ai-assistant`; merging remains with the repository owner.
