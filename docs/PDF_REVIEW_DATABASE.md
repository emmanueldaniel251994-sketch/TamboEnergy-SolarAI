# Persistent PDF provenance reviews

PDF review API decisions now use `manufacturer_pdf_reviews` rather than writing the local `review_decisions.jsonl` file. Each new decision and its audit log are committed in one database transaction. The API offers append, history, and readiness views; it exposes no review editing or deletion operation. This is not tamper-proof against database administrators.

Reviews remain separate from manufacturer knowledge verification. An approval can establish readiness for a separate evidence review, but never changes manufacturer, model, technical-document, or fault-code verification. Current stored-PDF integrity must be confirmed before adding a review or reporting readiness. Historical database reviews remain readable if PDF storage later becomes unavailable.

## Deployment requirement

Run `alembic upgrade head` **before serving the updated API**. The new head is `a8d52f4c901e`, following `0c7151855e86`. The repository Docker startup command already runs migrations; other launch configurations must do so explicitly. No migration was run against production during this work.

The table records document fingerprint, decision, reviewer user reference and durable identity snapshot, note, evidence URL, timestamp, and optional legacy import key. Deleting a user clears the foreign-key reference while preserving the historical reviewer snapshot. The API requires an active administrator and validates HTTPS provenance references. Review history returns the latest 100 decisions in ascending order; readiness uses the latest persisted ID, not a client timestamp.

PDF bytes and their metadata still require durable `SOLARAI_PENDING_PDF_DIR` storage. Moving the review history to the database does not move, back up, or restore the PDFs themselves.

## Legacy journals

Existing journal files are preserved and never automatically imported, deleted, or trusted as current database approvals. Inspect and back them up before switching deployment versions.

An operator with database access can preview an import after the schema migration:

```sh
cd backend
python migrate_pdf_review_journal.py --journal /path/to/review_decisions.jsonl --actor-user-id 1
```

Replace `1` with the actual active administrator responsible for the import. The default command is a dry run. After reviewing its summary and the journal provenance, the operator may explicitly add `--commit`. Do not run the write operation against production without the repository owner's approval.

The importer validates the complete batch before writing, accepts up to 5 MB / 1000 entries, rejects corrupt rows, and commits snapshots plus audit events atomically. Stable per-line import keys prevent re-importing an unchanged entry. Legacy reviewer IDs are historical claims, not re-authenticated identities; they are preserved as snapshots and are not linked to a current user.

Imported provenance approvals **cannot establish readiness**. A fresh administrator review of the current PDF and independent evidence is required. A later rejection or request for more evidence also prevents readiness. No import changes document verification or deletes the original file.

## Validation and limits

The complete backend suite passed **187 tests**, covering persistent history, atomic rollback, PDF tampering, admin authorization, evidence validation, dry-run and idempotent imports, corrupt batch rejection, fresh review requirements, reviewer deletion, and the public API contract. Migration upgrade, downgrade, and re-upgrade succeeded on a temporary SQLite database. Existing deprecation warnings remain.

Live PostgreSQL migration, concurrent multi-instance imports, and production restore drills were not executed. The unique legacy key protects against duplicate inserts; a concurrent import conflict rolls back rather than partially importing. Operators should serialize import runs.

Downgrading drops the new review table and its history; it does not export reviews back to JSONL. Preserve a database backup and export before a production rollback. No production deployment or data changes were performed.
