"""Actual PDF worker fixtures and failure/credential-boundary regression cases."""
import base64
import io
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from app.main import app
from app.database import get_db
from app.security import get_current_user
from app.services import manufacturer_pdf_intake as intake


def pdf(pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=300)
    if encrypted:
        writer.encrypt('synthetic-password')
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_worker_rejects_excess_pages():
    with pytest.raises(intake.PdfIntakeError):
        intake.inspect_pdf(pdf(pages=81))


def test_worker_rejects_encrypted_document():
    with pytest.raises(intake.PdfIntakeError):
        intake.inspect_pdf(pdf(encrypted=True))


@pytest.mark.skipif(sys.platform != 'linux', reason='Production parser limits are validated on Linux')
def test_production_worker_with_limits_parses_synthetic_pdf(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    assert intake.inspect_pdf(pdf())['pages'] == 1


def test_timeout_releases_processing_slot(monkeypatch):
    original = intake.subprocess.run
    monkeypatch.setattr(intake.subprocess, 'run', lambda *args, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired(args[0], 10)))
    with pytest.raises(intake.PdfIntakeError, match='timed out'):
        intake.inspect_pdf(pdf())
    monkeypatch.setattr(intake.subprocess, 'run', original)
    assert intake.inspect_pdf(pdf())['verification_status'] == 'pending'


def test_worker_crash_is_not_a_valid_document(monkeypatch):
    monkeypatch.setattr(intake.subprocess, 'run', lambda *args, **kw: SimpleNamespace(returncode=-9))
    with pytest.raises(intake.PdfIntakeError, match='resource limits'):
        intake.inspect_pdf(pdf())


@pytest.mark.parametrize('output', [b'invalid JSON', b'{"result":{"pages":999}}', b'x' * (intake.MAX_WORKER_OUTPUT + 1)])
def test_invalid_or_oversized_worker_output_rejected(monkeypatch, output):
    def fake(*args, **kwargs):
        kwargs['stdout'].write(output)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(intake.subprocess, 'run', fake)
    with pytest.raises(intake.PdfIntakeError):
        intake.inspect_pdf(pdf())


@pytest.mark.skipif(sys.platform != 'linux', reason='Production parser limits are validated on Linux')
def test_worker_does_not_receive_application_secrets(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'synthetic-secret-not-for-worker')
    monkeypatch.setenv('DATABASE_URL', 'synthetic-db-not-for-worker')
    monkeypatch.setenv('APP_ENV', 'production')
    original = intake.subprocess.run
    seen = {}
    def inspect(command, **kwargs):
        seen.update(kwargs)
        assert '-I' in command
        assert '--require-limits' in command
        return original(command, **kwargs)
    monkeypatch.setattr(intake.subprocess, 'run', inspect)
    intake.inspect_pdf(pdf())
    assert 'SECRET_KEY' not in seen['env']
    assert 'DATABASE_URL' not in seen['env']
    assert seen['timeout'] == 10


def test_processing_concurrency_is_bounded():
    intake._WORKERS.acquire()
    intake._WORKERS.acquire()
    try:
        with pytest.raises(intake.PdfIntakeBusyError):
            intake.inspect_pdf(pdf())
    finally:
        intake._WORKERS.release()
        intake._WORKERS.release()


@pytest.fixture
def api():
    app.dependency_overrides[get_db] = lambda: SimpleNamespace(get=lambda *args: object())
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='admin', is_active=1)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def payload():
    return {'equipment_model_id': 1, 'title': 'Synthetic manual', 'source_url': 'https://example.test/manual.pdf',
            'pdf_base64': base64.b64encode(pdf()).decode(), 'commit': False}


def test_production_intake_disabled_by_default(api, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.delenv('SOLARAI_PDF_INTAKE_ENABLED', raising=False)
    response = api.post('/manufacturer-knowledge/documents/pdf-intake', json=payload())
    assert response.status_code == 503
    assert 'disabled' in response.json()['detail']


def test_customer_cannot_access_pdf_parser(api):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role='customer', is_active=1)
    assert api.post('/manufacturer-knowledge/documents/pdf-intake', json=payload()).status_code == 403


def test_busy_api_has_retry_response(api, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    intake._WORKERS.acquire()
    intake._WORKERS.acquire()
    try:
        response = api.post('/manufacturer-knowledge/documents/pdf-intake', json=payload())
        assert response.status_code == 503
        assert response.headers['Retry-After'] == '10'
    finally:
        intake._WORKERS.release()
        intake._WORKERS.release()
