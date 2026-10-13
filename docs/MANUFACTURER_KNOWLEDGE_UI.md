# Manufacturer knowledge interface

Open **Equipment Knowledge** from the application navigation. Authenticated users can browse manufacturers, choose equipment models, open registered source documents, and see fault codes returned by the backend's fully verified evidence-chain lookup. Pending and revoked records retain visible status and are not presented as verified fault explanations.

Administrators additionally see registration forms for manufacturers, models, document links, and fault codes; record verification/revocation controls; and the existing pending-PDF provenance review workflow. The server continues to enforce administrator authorization for writes and PDF review.

## Administrator workflow

1. Register the manufacturer, model, source document link, and source-linked fault code. New records remain pending.
2. Independently review reliable evidence. Verify the manufacturer first, then the model, document, and fault code. Document verification requires the evidence URL to match the registered document URL.
3. Use **Review** to enter the HTTPS evidence reference and review note. The backend records the verification audit trail and rejects incomplete dependency chains.
4. Revoke a record with a reason when verification is no longer justified. Revocation also revokes dependent records; the interface explains this before submission.
5. Use **Load pending PDFs** to inspect stored PDF integrity and provenance review readiness. Record rejection, a request for more evidence, or provenance approval. This journal decision does not verify a manufacturer/database record.

Registration of a document link does not download or parse its PDF. The interface adds no upload UI or automatic promotion of pending content. Subsequent backend work added bounded PDF workers and transactional review history; see `PDF_PROCESSING_LIMITS.md` and `PDF_REVIEW_DATABASE.md`. Existing PDF review requires configured durable `SOLARAI_PENDING_PDF_DIR` storage; configuration errors are shown without claiming review success.

## Validation

Frontend component tests cover customer access without admin actions, pending registration without implicit verification, evidence verification payloads, provenance decisions without database verification, and unavailable PDF storage. The complete frontend suite has 10 passing tests. Production build and lint pass with existing application warnings. Real-browser rendering and deployed end-to-end integration remain unverified.

The backend is unchanged. Its previously verified 161-test suite remains the starting baseline. Registry endpoints currently return bounded lists (up to 200 records, or the configured PDF inventory limit); this interface is not a paginated inventory for larger installations.

## Branch state

This PR is based on the merged assistant changes on `codex/project-continuation`. At the start of this work, PR #2 was merged into that branch and PR #1 was still open against `feature/phase-2-ai-assistant`. Review this change separately; the repository owner controls merging and deployment.
