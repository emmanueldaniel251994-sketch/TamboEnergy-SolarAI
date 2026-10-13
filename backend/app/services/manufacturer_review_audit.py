"""Read-only audit of Phase 3J review journal; never promotes records."""
import hashlib
import json
from pathlib import Path
from app.services.manufacturer_review_decisions import decision_path, DIGEST, DecisionError
from app.services.manufacturer_pdf_review import review_one, ReviewError

MAX_JOURNAL = 5_000_000


def audit_review(storage_dir, sha256):
    if not isinstance(sha256, str) or not DIGEST.fullmatch(sha256):
        raise DecisionError('Invalid SHA-256 identifier')
    integrity = {'valid': False, 'reason': None}
    try:
        review_one(storage_dir, sha256)
        integrity['valid'] = True
    except (ReviewError, OSError, ValueError) as exc:
        integrity['reason'] = str(exc)[:180]
    journal = decision_path(storage_dir)
    if journal.is_symlink():
        raise DecisionError('Unsafe review journal symlink')
    entries = []
    issues = []
    if journal.exists():
        if not journal.is_file() or journal.stat().st_size > MAX_JOURNAL:
            raise DecisionError('Review journal invalid or too large')
        with journal.open('rb') as handle:
            for line_no, line in enumerate(handle, 1):
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict) or not DIGEST.fullmatch(str(item.get('sha256', ''))):
                        raise ValueError('Invalid journal entry')
                    if item['sha256'] == sha256:
                        if item.get('decision') not in {'approve_provenance', 'reject', 'needs_more_evidence'}:
                            issues.append(f'Invalid decision at line {line_no}')
                        entries.append(item)
                except (ValueError, UnicodeError, TypeError, KeyError):
                    issues.append(f'Corrupt journal entry at line {line_no}')
    last = entries[-1] if entries else None
    if not integrity['valid']:
        issues.append('Stored PDF integrity cannot be confirmed')
    if last is None:
        issues.append('No recorded human review')
    elif last.get('decision') != 'approve_provenance':
        issues.append('Latest review is not a provenance approval')
    elif not str(last.get('evidence_url') or '').startswith('https://'):
        issues.append('Latest provenance approval lacks HTTPS evidence URL')
    # A readiness flag is advisory; never equivalent to manufacturer authenticity.
    return {
        'sha256': sha256,
        'pdf_integrity': integrity,
        'review_count': len(entries),
        'latest_review': last,
        'issues': issues,
        'ready_for_separate_verification': not issues,
        'database_verification_changed': False,
        'journal_sha256': hashlib.sha256(journal.read_bytes()).hexdigest() if journal.is_file() and not journal.is_symlink() else None,
        'warning': 'A hash of the journal is not tamper-proof unless anchored externally. Approval requires independent source verification.',
    }
