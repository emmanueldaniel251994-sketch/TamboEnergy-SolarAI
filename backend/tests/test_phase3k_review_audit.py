"""Isolated review readiness tests; no production DB or external network."""
import json
import hashlib
import pytest
from app.services import manufacturer_review_audit as audit

DIGEST = hashlib.sha256(b'fixture').hexdigest()

@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'review_one', lambda path, digest: True)
    return tmp_path

def write(folder, decision='approve_provenance', evidence='https://manufacturer.example/manual'):
    entry = {'sha256': DIGEST, 'decision': decision, 'evidence_url': evidence, 'reviewer_id': '1'}
    (folder / 'review_decisions.jsonl').write_text(json.dumps(entry) + '\n')

def test_missing_review_not_ready(folder):
    assert not audit.audit_review(folder, DIGEST)['ready_for_separate_verification']

def test_approved_review_is_only_ready_for_separate_verification(folder):
    write(folder)
    result = audit.audit_review(folder, DIGEST)
    assert result['ready_for_separate_verification']
    assert result['database_verification_changed'] is False

def test_rejected_review_not_ready(folder):
    write(folder, decision='reject')
    assert not audit.audit_review(folder, DIGEST)['ready_for_separate_verification']

def test_missing_evidence_not_ready(folder):
    write(folder, evidence=None)
    assert not audit.audit_review(folder, DIGEST)['ready_for_separate_verification']

def test_corrupt_journal_not_ready(folder):
    (folder / 'review_decisions.jsonl').write_text('invalid json\n')
    assert not audit.audit_review(folder, DIGEST)['ready_for_separate_verification']

def test_bad_digest_rejected(folder):
    with pytest.raises(audit.DecisionError):
        audit.audit_review(folder, '../bad')

def test_integrity_failure_not_ready(folder, monkeypatch):
    monkeypatch.setattr(audit, 'review_one', lambda *args: (_ for _ in ()).throw(audit.ReviewError('hash mismatch')))
    write(folder)
    assert not audit.audit_review(folder, DIGEST)['ready_for_separate_verification']

def test_journal_hash_is_reported(folder):
    write(folder)
    assert len(audit.audit_review(folder, DIGEST)['journal_sha256']) == 64
