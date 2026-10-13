"""Isolated filesystem-only provenance review tests."""
import hashlib
import json
import pytest
from app.services.manufacturer_pdf_review import ReviewError, review_one, review_inventory

@pytest.fixture
def stored(tmp_path):
    payload = b'%PDF-1.4\nsynthetic integrity fixture'
    sha = hashlib.sha256(payload).hexdigest()
    (tmp_path / f'{sha}.pdf').write_bytes(payload)
    (tmp_path / f'{sha}.json').write_text(json.dumps({
        'sha256': sha, 'title': 'Synthetic test', 'source_url': 'https://example.com/test.pdf',
        'equipment_model_id': 1, 'pages': 1, 'verification_status': 'pending'}))
    return tmp_path, sha

def test_valid_document_integrity(stored):
    root, sha = stored
    result = review_one(str(root), sha)
    assert result['integrity_ok'] is True
    assert result['publisher_authenticity_verified'] is False

def test_inventory(stored):
    root, _ = stored
    assert review_inventory(str(root))['count'] == 1

def test_empty_inventory(tmp_path):
    assert review_inventory(str(tmp_path))['count'] == 0

def test_bad_digest_rejected(stored):
    root, _ = stored
    with pytest.raises(ReviewError): review_one(str(root), '../bad')

def test_missing_document_rejected(stored):
    root, _ = stored
    with pytest.raises(ReviewError): review_one(str(root), '0' * 64)

def test_tampered_pdf_rejected(stored):
    root, sha = stored
    (root / f'{sha}.pdf').write_bytes(b'tampered')
    with pytest.raises(ReviewError, match='integrity'): review_one(str(root), sha)

def test_tampered_metadata_rejected(stored):
    root, sha = stored
    (root / f'{sha}.json').write_text(json.dumps({'sha256': '0'*64, 'verification_status':'pending'}))
    with pytest.raises(ReviewError, match='fingerprint'): review_one(str(root), sha)

def test_verified_metadata_not_accepted(stored):
    root, sha = stored
    (root / f'{sha}.json').write_text(json.dumps({'sha256': sha, 'verification_status':'verified'}))
    with pytest.raises(ReviewError, match='status'): review_one(str(root), sha)
