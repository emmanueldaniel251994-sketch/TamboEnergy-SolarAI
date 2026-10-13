"""Persistent review, migration/import, and admin API regression cases."""
import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.manufacturer_pdf_review import ManufacturerPDFReview
from app.models.user import User
from app.security import get_current_user
from app.services import manufacturer_pdf_reviews_db as reviews

NOTE = 'Independently reviewed document source and integrity.'
EVIDENCE = 'https://manufacturer.example/manual.pdf'


@pytest.fixture
def fixture(tmp_path):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(conn, record):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        db.add_all([User(id=1, full_name='Admin', email='admin@example.test', hashed_password='not-a-real-hash', role='admin', is_active=1),
                    User(id=2, full_name='Customer', email='customer@example.test', hashed_password='not-a-real-hash', role='customer', is_active=1)])
        db.commit()
    data = b'%PDF-1.4 synthetic integrity fixture'
    sha = hashlib.sha256(data).hexdigest()
    (tmp_path / f'{sha}.pdf').write_bytes(data)
    (tmp_path / f'{sha}.json').write_text(json.dumps({'sha256':sha,'verification_status':'pending'}))
    with sessions() as db:
        yield db, str(tmp_path), sha, sessions
    engine.dispose()


def record(fixture, decision='approve_provenance'):
    db, folder, sha, _ = fixture
    return reviews.record_review(db, folder, sha, decision, 1, EVIDENCE, NOTE)


def test_review_and_audit_persist_together(fixture):
    db, folder, sha, sessions = fixture
    result = record(fixture)
    assert result['effect'] == 'review_only_no_database_verification'
    with sessions() as reopened:
        assert len(reviews.review_history(reopened, sha)) == 1
        assert reopened.query(AuditLog).count() == 1
        assert reviews.review_audit(reopened, folder, sha)['ready_for_separate_verification']
    assert json.loads((__import__('pathlib').Path(folder) / f'{sha}.json').read_text())['verification_status'] == 'pending'


def test_rejection_supersedes_earlier_provenance_approval(fixture):
    db, folder, sha, _ = fixture
    record(fixture)
    record(fixture, 'reject')
    audit = reviews.review_audit(db, folder, sha)
    assert audit['review_count'] == 2
    assert audit['latest_review']['decision'] == 'reject'
    assert not audit['ready_for_separate_verification']


def test_failed_transaction_rolls_back_review_and_audit(fixture, monkeypatch):
    db, _, sha, _ = fixture
    monkeypatch.setattr(db, 'commit', lambda: (_ for _ in ()).throw(RuntimeError('synthetic commit failure')))
    with pytest.raises(RuntimeError):
        record(fixture)
    assert reviews.review_history(db, sha) == []
    assert db.query(AuditLog).count() == 0


def test_tampering_blocks_new_review_and_readiness(fixture):
    db, folder, sha, _ = fixture
    record(fixture)
    (__import__('pathlib').Path(folder) / f'{sha}.pdf').write_bytes(b'tampered')
    with pytest.raises(reviews.DecisionError):
        record(fixture, 'reject')
    assert db.query(ManufacturerPDFReview).count() == 1
    assert not reviews.review_audit(db, folder, sha)['ready_for_separate_verification']


@pytest.mark.parametrize('user_id', [2, 999])
def test_non_admin_or_unknown_reviewer_cannot_write(fixture, user_id):
    db, folder, sha, _ = fixture
    with pytest.raises(reviews.DecisionError):
        reviews.record_review(db, folder, sha, 'approve_provenance', user_id, EVIDENCE, NOTE)
    assert db.query(ManufacturerPDFReview).count() == 0


@pytest.mark.parametrize('url', [None, 'https://', 'https://user:password@example.test/manual'])
def test_invalid_approval_evidence_rejected(fixture, url):
    db, folder, sha, _ = fixture
    with pytest.raises(reviews.DecisionError):
        reviews.record_review(db, folder, sha, 'approve_provenance', 1, url, NOTE)
    assert db.query(ManufacturerPDFReview).count() == 0


def journal(fixture):
    _, folder, sha, _ = fixture
    path = __import__('pathlib').Path(folder) / 'review_decisions.jsonl'
    path.write_text(json.dumps({'sha256':sha,'decision':'approve_provenance','reviewer_id':'old-reviewer',
        'note':NOTE,'evidence_url':EVIDENCE,'timestamp':'2026-10-01T09:00:00+00:00'}) + '\n')
    return path


def test_legacy_import_is_dry_run_and_idempotent(fixture):
    db, folder, sha, _ = fixture
    path = journal(fixture)
    assert reviews.import_legacy_reviews(db, path, 1)['new_entries'] == 1
    assert db.query(ManufacturerPDFReview).count() == 0
    assert reviews.import_legacy_reviews(db, path, 1, commit=True)['committed']
    assert reviews.import_legacy_reviews(db, path, 1, commit=True)['new_entries'] == 0
    assert db.query(ManufacturerPDFReview).count() == 1
    audit = reviews.review_audit(db, folder, sha)
    assert not audit['ready_for_separate_verification']
    assert audit['latest_review']['imported_legacy']
    record(fixture)
    assert reviews.review_audit(db, folder, sha)['ready_for_separate_verification']
    assert path.exists()


def test_corrupt_legacy_import_writes_nothing(fixture):
    db, _, _, _ = fixture
    path = journal(fixture)
    with path.open('a') as handle:
        handle.write('not JSON\n')
    with pytest.raises(reviews.DecisionError):
        reviews.import_legacy_reviews(db, path, 1, commit=True)
    assert db.query(ManufacturerPDFReview).count() == 0
    assert db.query(AuditLog).count() == 0


def test_reviewer_deletion_preserves_snapshot(fixture):
    db, _, sha, _ = fixture
    record(fixture)
    db.delete(db.get(User, 1))
    db.commit()
    row = db.query(ManufacturerPDFReview).one()
    assert row.reviewer_user_id is None
    assert reviews.review_history(db, sha)[0]['reviewer_id'] == '1'


def test_routes_persist_and_restrict_database_reviews(fixture, monkeypatch):
    _, folder, sha, sessions = fixture
    monkeypatch.setenv('SOLARAI_PENDING_PDF_DIR', folder)
    def database():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='admin', is_active=1)
    prefix = f'/manufacturer-knowledge/documents/pending-review/{sha}'
    try:
        with TestClient(app) as api:
            response = api.post(prefix + '/decision', json={'decision':'approve_provenance','evidence_url':EVIDENCE,'note':NOTE})
            assert response.status_code == 200, response.text
            assert len(api.get(prefix + '/decisions').json()['decisions']) == 1
            assert api.get(prefix + '/audit').json()['storage'] == 'database'
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role='customer', is_active=1)
            for suffix in ['/decisions', '/audit']:
                assert api.get(prefix + suffix).status_code == 403
            assert api.post(prefix + '/decision', json={'decision':'reject','note':NOTE}).status_code == 403
    finally:
        app.dependency_overrides.clear()
