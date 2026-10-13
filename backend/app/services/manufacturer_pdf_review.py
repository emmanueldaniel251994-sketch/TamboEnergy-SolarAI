"""Read-only pending PDF review inventory; never changes verification status."""
import hashlib
import json
import re
from pathlib import Path

DIGEST = re.compile(r'^[0-9a-f]{64}$')

class ReviewError(ValueError):
    pass

def review_one(storage_dir: str, sha256: str) -> dict:
    if not DIGEST.fullmatch(sha256):
        raise ReviewError('Invalid SHA-256 identifier')
    root = Path(storage_dir).resolve()
    pdf = root / f'{sha256}.pdf'
    meta = root / f'{sha256}.json'
    if not pdf.is_file() or not meta.is_file() or pdf.is_symlink() or meta.is_symlink():
        raise ReviewError('Pending document not found')
    if pdf.stat().st_size > 8 * 1024 * 1024 or meta.stat().st_size > 32_768:
        raise ReviewError('Stored document exceeds configured limits')
    try:
        metadata = json.loads(meta.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReviewError('Invalid stored metadata') from exc
    if not isinstance(metadata, dict) or metadata.get('sha256') != sha256:
        raise ReviewError('Metadata fingerprint mismatch')
    if metadata.get('verification_status') != 'pending':
        raise ReviewError('Unexpected verification status')
    digest = hashlib.sha256()
    with pdf.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    if digest.hexdigest() != sha256:
        raise ReviewError('PDF integrity mismatch')
    return {
        'sha256': sha256,
        'title': metadata.get('title'),
        'source_url': metadata.get('source_url'),
        'equipment_model_id': metadata.get('equipment_model_id'),
        'pages': metadata.get('pages'),
        'bytes': pdf.stat().st_size,
        'verification_status': 'pending',
        'integrity_ok': True,
        'publisher_authenticity_verified': False,
        'review_required': True,
    }

def review_inventory(storage_dir: str, limit: int = 50) -> dict:
    root = Path(storage_dir).resolve()
    if not root.is_dir():
        return {'documents': [], 'errors': [], 'count': 0}
    docs, errors = [], []
    for path in sorted(root.glob('*.json'))[:limit]:
        try:
            docs.append(review_one(str(root), path.stem))
        except ReviewError as exc:
            errors.append({'sha256': path.stem, 'reason': str(exc)})
    return {'documents': docs, 'errors': errors, 'count': len(docs)}
