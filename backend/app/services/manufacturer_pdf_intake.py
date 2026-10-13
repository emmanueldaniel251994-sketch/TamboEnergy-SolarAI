"""Bounded PDF intake. This is not malware scanning or source verification."""
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from pypdf import PdfReader

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PAGES = 80
MAX_TEXT_CHARS = 100_000

class PdfIntakeError(ValueError):
    pass

def inspect_pdf(data: bytes) -> dict:
    if not data or len(data) > MAX_PDF_BYTES:
        raise PdfIntakeError('PDF must be nonempty and no larger than 8 MiB')
    if not data.startswith(b'%PDF-'):
        raise PdfIntakeError('Invalid PDF header')
    digest = hashlib.sha256(data).hexdigest()
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise PdfIntakeError('Encrypted PDFs are not supported')
        pages = len(reader.pages)
        if pages < 1 or pages > MAX_PAGES:
            raise PdfIntakeError('PDF must have 1 to 80 pages')
        parts, count = [], 0
        for page in reader.pages:
            remaining = MAX_TEXT_CHARS - count
            if remaining <= 0:
                break
            # pypdf is not a hardened sandbox; never use this on untrusted public uploads without isolation.
            text = page.extract_text() or ''
            text = text[:remaining]
            parts.append(text)
            count += len(text)
    except PdfIntakeError:
        raise
    except Exception as exc:
        raise PdfIntakeError('PDF parsing failed') from exc
    return {'sha256': digest, 'bytes': len(data), 'pages': pages,
            'extracted_chars': count, 'text': '\n\n'.join(parts),
            'truncated': count >= MAX_TEXT_CHARS, 'verification_status': 'pending'}

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
