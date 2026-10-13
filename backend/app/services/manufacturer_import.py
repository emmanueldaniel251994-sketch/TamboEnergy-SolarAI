"""Preview-first, pending-only manufacturer fault-code importer.

No document downloading or automatic trust promotion occurs here.
"""
import csv
import io
import json
from sqlalchemy.orm import Session
from app.models.manufacturer_knowledge import EquipmentModel, TechnicalDocument, EquipmentFaultCode

MAX_BYTES = 512_000
MAX_ROWS = 500
FIELDS = {'equipment_model_id', 'source_document_id', 'fault_code', 'description', 'severity', 'recommended_action'}


def parse_import(content: bytes, format_name: str):
    if not content or len(content) > MAX_BYTES:
        raise ValueError('Import must be nonempty and at most 512 KB')
    try:
        text = content.decode('utf-8-sig')
        if format_name == 'csv':
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames or not FIELDS.issuperset(reader.fieldnames) or not {'equipment_model_id','source_document_id','fault_code','description'}.issubset(reader.fieldnames):
                raise ValueError('Invalid CSV columns')
            rows = list(reader)
        elif format_name == 'json':
            rows = json.loads(text)
        else:
            raise ValueError('Use csv or json')
    except (UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        raise ValueError('Malformed import file') from exc
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError('Expected a list of up to 500 rows')
    if any(not isinstance(r, dict) for r in rows):
        raise ValueError('Every row must be an object')
    return rows


def prepare_import(db: Session, rows):
    """Validate entire batch; do not write until caller explicitly commits."""
    accepted, rejected, skipped = [], [], []
    seen = set()
    for line, raw in enumerate(rows, 1):
        try:
            if set(raw) - FIELDS:
                raise ValueError('Unexpected field')
            model_id, doc_id = int(raw['equipment_model_id']), int(raw['source_document_id'])
            if model_id <= 0 or doc_id <= 0:
                raise ValueError('Invalid IDs')
            code = str(raw['fault_code']).strip()
            description = str(raw['description']).strip()
            severity = str(raw.get('severity') or 'unknown').strip()
            action = str(raw.get('recommended_action') or '').strip()
            if not code or len(code) > 100 or not description or len(description) > 4000 or len(action) > 4000 or len(severity) > 50:
                raise ValueError('Invalid fault fields')
            model = db.get(EquipmentModel, model_id)
            doc = db.get(TechnicalDocument, doc_id)
            if not model or not doc or doc.equipment_model_id != model_id:
                raise ValueError('Document does not belong to equipment model')
            key = (model_id, code)
            if key in seen:
                skipped.append({'row': line, 'reason': 'Duplicate code in batch'})
                continue
            seen.add(key)
            existing = db.query(EquipmentFaultCode).filter_by(equipment_model_id=model_id, fault_code=code).first()
            if existing:
                skipped.append({'row': line, 'reason': 'Code already exists; no overwrite'})
                continue
            accepted.append({'row': line, 'equipment_model_id': model_id, 'source_document_id': doc_id,
                             'fault_code': code, 'description': description, 'severity': severity,
                             'recommended_action': action})
        except (KeyError, ValueError, TypeError) as exc:
            rejected.append({'row': line, 'reason': str(exc)[:160]})
    return {'accepted': accepted, 'rejected': rejected, 'skipped': skipped}


def import_pending(db: Session, report):
    if report['rejected']:
        raise ValueError('Rejected rows present: fix input before committing')
    try:
        for item in report['accepted']:
            data = {k: v for k, v in item.items() if k != 'row'}
            db.add(EquipmentFaultCode(**data, verification_status='pending'))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(report['accepted'])
