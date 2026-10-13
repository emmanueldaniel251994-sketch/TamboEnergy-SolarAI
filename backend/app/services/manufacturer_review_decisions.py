"""Human review decisions in a separate append-only journal, not DB approval."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from app.services.manufacturer_pdf_review import review_one, ReviewError

DIGEST = re.compile(r"^[0-9a-f]{64}$")
DECISIONS = {"approve_provenance", "reject", "needs_more_evidence"}

class DecisionError(ValueError):
    pass

def decision_path(storage_dir):
    return Path(storage_dir).resolve() / "review_decisions.jsonl"

def record_decision(storage_dir, sha256, decision, reviewer_id, evidence_url, note):
    if not DIGEST.fullmatch(sha256) or decision not in DECISIONS:
        raise DecisionError("Invalid identifier or decision")
    if not isinstance(note, str) or not (20 <= len(note.strip()) <= 2000):
        raise DecisionError("Review note must contain 20 to 2000 characters")
    if decision == "approve_provenance":
        if not isinstance(evidence_url, str) or not evidence_url.startswith("https://") or len(evidence_url) > 2048:
            raise DecisionError("Approval requires an HTTPS provenance reference")
    if evidence_url and (not isinstance(evidence_url, str) or len(evidence_url) > 2048):
        raise DecisionError("Invalid evidence URL")
    try:
        review_one(storage_dir, sha256)  # ensure integrity before recording a review
    except ReviewError as exc:
        raise DecisionError(str(exc)) from exc
    journal = decision_path(storage_dir)
    if journal.is_symlink():
        raise DecisionError("Review journal must not be a symbolic link")
    entry = {"sha256": sha256, "decision": decision, "reviewer_id": str(reviewer_id),
             "evidence_url": evidence_url, "note": note.strip(),
             "timestamp": datetime.now(timezone.utc).isoformat(),
             "effect": "review_only_no_database_verification"}
    # Exclusive creation prevents overwriting; append-only is best-effort on local filesystems.
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(journal), flags, 0o600)
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        raise
    return entry

def decision_history(storage_dir, sha256, max_entries=100):
    if not DIGEST.fullmatch(sha256):
        raise DecisionError("Invalid identifier")
    try:
        review_one(storage_dir, sha256)
    except ReviewError as exc:
        raise DecisionError(str(exc)) from exc
    journal = decision_path(storage_dir)
    if not journal.exists():
        return []
    if journal.is_symlink() or journal.stat().st_size > 5_000_000:
        raise DecisionError("Unsafe or oversized review journal")
    results = []
    with journal.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError as exc:
                raise DecisionError("Corrupt review journal") from exc
            if entry.get("sha256") == sha256:
                results.append(entry)
    return results[-max_entries:]
