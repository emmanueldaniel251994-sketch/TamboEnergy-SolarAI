"""Bounded PDF intake. This is not malware scanning or source verification."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import threading

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PAGES = 80
MAX_TEXT_CHARS = 100_000

class PdfIntakeError(ValueError):
    pass

# Limits are per API process. Deployment concurrency must also be bounded.
MAX_WORKER_OUTPUT = 800_000
PDF_WORKER_TIMEOUT = 10
_WORKERS = threading.BoundedSemaphore(2)

class PdfIntakeBusyError(PdfIntakeError):
    pass


def inspect_pdf(data: bytes) -> dict:
    if not data or len(data) > MAX_PDF_BYTES:
        raise PdfIntakeError('PDF must be nonempty and no larger than 8 MiB')
    if not data.startswith(b'%PDF-'):
        raise PdfIntakeError('Invalid PDF header')
    if not _WORKERS.acquire(blocking=False):
        raise PdfIntakeBusyError('PDF processing is busy; retry later')
    try:
        worker = Path(__file__).with_name('manufacturer_pdf_worker.py').resolve()
        command = [sys.executable, '-I', str(worker)]
        if os.environ.get('APP_ENV', '').strip().lower() == 'production':
            command.append('--require-limits')
        # An allowlist excludes API/database credentials and Python path overrides.
        environment = {key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR', 'LANG') if key in os.environ}
        with tempfile.TemporaryDirectory(prefix='solarai-pdf-') as directory:
            with tempfile.TemporaryFile() as output:
                process = subprocess.run(command, input=data, stdout=output, stderr=subprocess.DEVNULL,
                    cwd=directory, env=environment, timeout=PDF_WORKER_TIMEOUT, check=False)
                output.seek(0)
                raw = output.read(MAX_WORKER_OUTPUT + 1)
        if process.returncode != 0 or not raw or len(raw) > MAX_WORKER_OUTPUT:
            raise PdfIntakeError('PDF parsing failed or exceeded resource limits')
        try:
            payload = json.loads(raw)
            result = payload['result']
            pages, count, text = result['pages'], result['extracted_chars'], result['text']
            if (type(pages) is not int or not 1 <= pages <= MAX_PAGES
                    or type(count) is not int or not 0 <= count <= MAX_TEXT_CHARS
                    or not isinstance(text, str) or len(text) > MAX_TEXT_CHARS + 2 * MAX_PAGES
                    or type(result['truncated']) is not bool):
                raise ValueError('Invalid parser result')
        except (ValueError, TypeError, KeyError):
            raise PdfIntakeError('PDF parsing failed or exceeded resource limits') from None
        return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'pages': pages,
                'extracted_chars': count, 'text': text, 'truncated': result['truncated'],
                'verification_status': 'pending'}
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for the child before raising.
        raise PdfIntakeError('PDF processing timed out') from None
    except OSError:
        raise PdfIntakeError('PDF processing worker is unavailable') from None
    finally:
        _WORKERS.release()

def save_pending_pdf(data: bytes, report: dict, equipment_model_id: int,
                     title: str, source_url: str, storage_dir: str) -> dict:
    """Atomic immutable-by-digest storage, no database approval or verified status."""
    base = Path(storage_dir).resolve()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    digest = report['sha256']
    pdf_path = base / (digest + '.pdf')
    meta_path = base / (digest + '.json')
    if pdf_path.exists() or meta_path.exists():
        raise PdfIntakeError('Document fingerprint already exists; no overwrite')
    meta = {'sha256': digest, 'bytes': report['bytes'], 'pages': report['pages'],
            'extracted_chars': report['extracted_chars'], 'truncated': report['truncated'],
            'equipment_model_id': equipment_model_id, 'title': title,
            'source_url': source_url, 'verification_status': 'pending',
            'review_required': True}
    # Files are created exclusively. If metadata fails, remove PDF so retry is possible.
    try:
        with pdf_path.open('xb') as handle:
            handle.write(data)
        try:
            with meta_path.open('x', encoding='utf-8') as handle:
                json.dump(meta, handle, indent=2)
        except Exception:
            pdf_path.unlink(missing_ok=True)
            raise
    except FileExistsError as exc:
        raise PdfIntakeError('Document fingerprint already exists') from exc
    return meta
