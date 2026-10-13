# PDF processing limits

PDF intake now sends validated, size-limited bytes to a short-lived Python parser process instead of importing and running the PDF parser in the API process. The public report format and pending verification status are unchanged. No document is automatically verified or promoted.

## Limits

| Boundary | Limit |
| --- | --- |
| Input PDF | 8 MiB, PDF header required |
| Document | 1–80 pages, unencrypted |
| Extracted text | 100,000 characters, plus page separators |
| Child wall time | 10 seconds; timed-out child is killed and awaited |
| Linux child CPU time | 5 seconds |
| Linux child address space | 256 MiB |
| Worker output / file size | 800,000 bytes |
| Simultaneous parsers | 2 per API process |

The child uses isolated Python mode, a temporary working directory, and an environment allowlist that excludes API/database credentials and Python import path overrides. It receives PDF bytes through stdin rather than storage paths. Error responses omit parser exception details, filesystem paths, and extracted document text. The parent validates worker output and computes the input fingerprint itself.

The isolated interpreter must be able to import the installed `pypdf` dependency. Use the documented virtual environment or container installation; user-site-only installations are not available in isolated mode.

## Production behavior

Production PDF intake is **disabled by default**. The production example explicitly sets `SOLARAI_PDF_INTAKE_ENABLED=false`; disabled intake returns HTTP 503. Stored-document review and non-PDF knowledge registration are unaffected.

Enable intake only after reviewing the deployment boundary and durable pending storage. `SOLARAI_PDF_INTAKE_ENABLED=true` opts in; production workers require operating-system resource limit support. Linux is the validated production platform. Development on Windows retains wall-time, input/output, and concurrency bounds but does not claim Linux memory/CPU enforcement.

These limits reduce parser denial-of-service exposure. They are not malware scanning, publisher authentication, network isolation, or a complete security sandbox. The child still has the operating-system privileges of the API user. A deployment that accepts untrusted PDFs needs restricted process/container permissions, appropriate network and filesystem isolation, and resource limits across all API workers/instances. Review decisions now use transactional database storage; see `PDF_REVIEW_DATABASE.md` for migrations and legacy-journal handling.

Busy processing returns HTTP 503 with `Retry-After: 10`. Malformed, encrypted, excessive-page, failed, or timed-out parsing returns the existing controlled intake validation error. The authorization requirement remains administrator-only.

## Validation

The full backend suite passed **174 tests** on Linux, including actual synthetic PDF worker execution, encrypted/excessive-page rejection, production resource-limit execution, sanitized environment checks, timeout cleanup, worker crash rejection, invalid/oversized output, concurrency limits, production-disabled intake, administrator authorization, and busy retry behavior. Existing deprecation warnings remain.

Timeout and crash branches use injected failures to verify parent handling; this does not constitute exploit testing or a proof of complete containment. No production data, deployment configuration, or migrations were changed during validation.
