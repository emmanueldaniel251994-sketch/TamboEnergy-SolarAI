import hashlib
import json
import pytest
from app.services.manufacturer_review_decisions import (
    record_decision, decision_history, DecisionError,
)

@pytest.fixture
def pending(tmp_path):
    data = b"%PDF-1.4\\nsynthetic integrity-only fixture"
    digest = hashlib.sha256(data).hexdigest()
    (tmp_path / (digest + ".pdf")).write_bytes(data)
    (tmp_path / (digest + ".json")).write_text(json.dumps({
        "sha256": digest, "verification_status": "pending",
        "equipment_model_id": 1, "title": "Synthetic", "source_url": "https://example.test",
    }))
    return str(tmp_path), digest

NOTE = "Reviewed the synthetic document metadata and integrity."

def test_review_written(pending):
    folder, digest = pending
    entry = record_decision(folder, digest, "needs_more_evidence", 7, None, NOTE)
    assert entry["effect"] == "review_only_no_database_verification"

def test_review_history(pending):
    folder, digest = pending
    record_decision(folder, digest, "reject", 7, None, NOTE)
    assert len(decision_history(folder, digest)) == 1

def test_requires_evidence_for_approval(pending):
    folder, digest = pending
    with pytest.raises(DecisionError):
        record_decision(folder, digest, "approve_provenance", 7, None, NOTE)

def test_approval_is_only_a_journal_entry(pending):
    folder, digest = pending
    entry = record_decision(folder, digest, "approve_provenance", 7, "https://example.test/evidence", NOTE)
    assert entry["effect"] == "review_only_no_database_verification"
    assert json.loads((__import__("pathlib").Path(folder) / (digest + ".json")).read_text())["verification_status"] == "pending"

def test_invalid_digest(pending):
    folder, _ = pending
    with pytest.raises(DecisionError):
        record_decision(folder, "not-a-digest", "reject", 7, None, NOTE)

def test_short_note(pending):
    folder, digest = pending
    with pytest.raises(DecisionError):
        record_decision(folder, digest, "reject", 7, None, "short")

def test_tampered_pdf(pending):
    folder, digest = pending
    (__import__("pathlib").Path(folder) / (digest + ".pdf")).write_bytes(b"tampered")
    with pytest.raises(DecisionError):
        record_decision(folder, digest, "reject", 7, None, NOTE)

def test_history_empty(pending):
    folder, digest = pending
    assert decision_history(folder, digest) == []
