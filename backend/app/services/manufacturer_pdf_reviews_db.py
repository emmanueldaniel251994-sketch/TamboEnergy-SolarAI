"""Transactional review history. Provenance review never verifies knowledge records."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from app.models.audit_log import AuditLog
from app.models.manufacturer_pdf_review import ManufacturerPDFReview
from app.models.user import User
from app.services.manufacturer_pdf_review import review_one, ReviewError
from app.services.manufacturer_review_decisions import DecisionError, DECISIONS, DIGEST


def validate(sha256, decision, evidence_url, note):
    if not isinstance(sha256, str) or not DIGEST.fullmatch(sha256) or not isinstance(decision, str) or decision not in DECISIONS:
        raise DecisionError('Invalid identifier or decision')
    if not isinstance(note, str) or not 20 <= len(note.strip()) <= 2000:
        raise DecisionError('Review note must contain 20 to 2000 characters')
    if evidence_url is not None:
        if not isinstance(evidence_url, str) or len(evidence_url) > 2048:
            raise DecisionError('Invalid evidence URL')
        evidence_url = evidence_url.strip() or None
    if evidence_url:
        try:
            parsed = urlsplit(evidence_url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Invalid evidence URL')
        except ValueError:
            raise DecisionError('A valid HTTPS evidence URL is required') from None
    if decision == 'approve_provenance' and not evidence_url:
        raise DecisionError('Approval requires an HTTPS provenance reference')
    return evidence_url, note.strip()


def actor(db, reviewer_id):
    user = db.get(User, reviewer_id)
    if user is None or user.role != 'admin' or not user.is_active:
        raise DecisionError('An active administrator reviewer is required')
    return user


def view(record):
    timestamp = record.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return {'id': record.id, 'sha256': record.sha256, 'decision': record.decision,
            'reviewer_id': record.reviewer_reference, 'evidence_url': record.evidence_url,
            'note': record.note, 'timestamp': timestamp.isoformat(),
            'effect': 'review_only_no_database_verification', 'imported_legacy': record.legacy_key is not None}


def add_audit(db, record, user_id, action):
    db.add(AuditLog(user_id=user_id, action=action, resource_type='manufacturer_pdf_review',
        resource_id=record.id, details=json.dumps({'sha256': record.sha256, 'decision': record.decision,
            'imported_legacy': record.legacy_key is not None, 'database_verification_changed': False})))


def record_review(db, storage_dir, sha256, decision, reviewer_id, evidence_url, note):
    evidence_url, note = validate(sha256, decision, evidence_url, note)
    reviewer = actor(db, reviewer_id)
    try:
        review_one(storage_dir, sha256)
    except (ReviewError, OSError) as exc:
        raise DecisionError('Stored PDF integrity could not be confirmed') from exc
    record = ManufacturerPDFReview(sha256=sha256, decision=decision, reviewer_user_id=reviewer.id,
        reviewer_reference=str(reviewer.id), evidence_url=evidence_url, note=note)
    try:
        db.add(record)
        db.flush()
        add_audit(db, record, reviewer.id, 'manufacturer_pdf_provenance_reviewed')
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise
    return view(record)


def review_history(db, sha256, limit=100):
    if not isinstance(sha256, str) or not DIGEST.fullmatch(sha256) or not 1 <= limit <= 100:
        raise DecisionError('Invalid identifier or history limit')
    records = db.query(ManufacturerPDFReview).filter_by(sha256=sha256).order_by(
        ManufacturerPDFReview.id.desc()).limit(limit).all()
    return [view(record) for record in reversed(records)]


def review_audit(db, storage_dir, sha256):
    if not isinstance(sha256, str) or not DIGEST.fullmatch(sha256):
        raise DecisionError('Invalid SHA-256 identifier')
    integrity = {'valid': False, 'reason': None}
    try:
        review_one(storage_dir, sha256)
        integrity['valid'] = True
    except (ReviewError, OSError, ValueError):
        integrity['reason'] = 'Stored PDF integrity cannot be confirmed'
    query = db.query(ManufacturerPDFReview).filter_by(sha256=sha256)
    count = query.count()
    latest = query.order_by(ManufacturerPDFReview.id.desc()).first()
    issues = []
    if not integrity['valid']:
        issues.append('Stored PDF integrity cannot be confirmed')
    if latest is None:
        issues.append('No recorded database review')
    elif latest.legacy_key is not None:
        issues.append('Imported legacy review requires a new administrator review')
    elif latest.decision != 'approve_provenance':
        issues.append('Latest review is not a provenance approval')
    else:
        try:
            validate(sha256, latest.decision, latest.evidence_url, latest.note)
        except DecisionError:
            issues.append('Latest review has invalid provenance evidence')
    return {'sha256': sha256, 'pdf_integrity': integrity, 'review_count': count,
        'latest_review': view(latest) if latest else None, 'issues': issues,
        'ready_for_separate_verification': not issues, 'database_verification_changed': False,
        'storage': 'database', 'journal_sha256': None,
        'legacy_journal_present': (Path(storage_dir) / 'review_decisions.jsonl').exists(),
        'warning': 'Database administrators can alter records. Readiness is advisory and never manufacturer verification.'}


def import_legacy_reviews(db, journal_path, actor_id, commit=False):
    """Explicit operator tool. Imported history cannot establish review readiness."""
    actor(db, actor_id)
    path = Path(journal_path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 5_000_000:
        raise DecisionError('Invalid or oversized legacy review journal')
    with path.open('rb') as handle:
        raw = handle.read(5_000_001)
    if len(raw) > 5_000_000:
        raise DecisionError('Legacy journal exceeds size limit')
    records = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        if len(records) >= 1000:
            raise DecisionError('Legacy import is limited to 1000 entries')
        try:
            item = json.loads(line)
            evidence, note = validate(item['sha256'], item['decision'], item.get('evidence_url'), item['note'])
            reference = item['reviewer_id']
            if type(reference) not in (str, int) or not 1 <= len(str(reference)) <= 120:
                raise ValueError('Invalid reviewer')
            timestamp = datetime.fromisoformat(item['timestamp'])
            if timestamp.tzinfo is None:
                raise ValueError('Timestamp must include timezone')
            canonical = json.dumps(item, sort_keys=True, separators=(',', ':'))
            key = hashlib.sha256(f'{line_no}:{canonical}'.encode()).hexdigest()
        except (ValueError, TypeError, KeyError, DecisionError):
            raise DecisionError(f'Invalid legacy entry at line {line_no}; nothing imported') from None
        records.append(ManufacturerPDFReview(sha256=item['sha256'], decision=item['decision'],
            reviewer_reference=str(reference), reviewer_user_id=None, evidence_url=evidence,
            note=note, created_at=timestamp.astimezone(timezone.utc), legacy_key=key))
    existing = {row[0] for row in db.query(ManufacturerPDFReview.legacy_key).filter(
        ManufacturerPDFReview.legacy_key.in_([record.legacy_key for record in records])).all()}
    new = [record for record in records if record.legacy_key not in existing]
    result = {'entries': len(records), 'new_entries': len(new), 'already_imported': len(records) - len(new),
              'committed': False, 'database_verification_changed': False, 'requires_fresh_review': True}
    if commit:
        try:
            for record in new:
                db.add(record)
                db.flush()
                add_audit(db, record, actor_id, 'manufacturer_pdf_legacy_review_imported')
            db.commit()
        except Exception:
            db.rollback()
            raise
        result['committed'] = True
    return result
