# Saved diagnostic cases

The AI Assistant now uses the existing authenticated conversation APIs. Start a case with a complaint and optional reported equipment details, send follow-up messages, and reopen a case from the saved list. The server owns the history; a page reload does not require recreating the case.

Equipment inputs show the saved profile. Only edited, nonempty fields are sent on a follow-up, allowing the backend to extract new readings from the latest message without overwriting them with old displayed values. An empty edit leaves the saved value unchanged. Reported details are not manufacturer verification. Guidance displays available safety notices, questions, possible causes, checks, solutions, and evidence references.

The earlier stateless advice endpoint remains available under **Ask about a telemetry record**. Saved conversations are a separate workflow and do not automatically attach a telemetry record or establish manufacturer grounding.

## Validation

- Backend regression suite: **161 passed**, including seven API tests for create/list/reopen, follow-up persistence, explicit reading precedence, invalid update rollback, cross-user isolation, and blank input rejection.
- Frontend DOM tests: **5 passed** for case creation, follow-up payloads and reopening, error preservation, expired sessions/retry, and whitespace rejection.
- Frontend lint and production build: succeeded with existing effect and bundle-size warnings.
- Browser rendering QA was attempted but could not run because the browser download failed. The DOM tests exercise component interaction with mocked HTTP responses; they do not establish real-browser layout or a deployed end-to-end flow.

Run frontend checks with Node.js 24.15 or later within the Node.js 24 release line:

```sh
cd frontend
npm ci
npm test
npm run lint
npm run build
```

CI uses Node.js 24 for the frontend test dependencies. No database migration, production deployment, or merge is part of this change.

## Review sequence

This change is based on `codex/project-continuation` (PR #1). Review and merge PR #1 into `feature/phase-2-ai-assistant` first; retarget this PR to that development branch afterward. Merging remains with the repository owner.
