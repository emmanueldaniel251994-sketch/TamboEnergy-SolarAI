"""Phase 3B: evidence-gated verification, revocation, trusted lookup."""
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.manufacturer_knowledge import Manufacturer, EquipmentModel, TechnicalDocument, EquipmentFaultCode

MODELS = {"manufacturer": Manufacturer, "equipment_model": EquipmentModel,
          "technical_document": TechnicalDocument, "fault_code": EquipmentFaultCode}


def _resource(db, kind, resource_id):
    if kind not in MODELS or resource_id < 1:
        raise HTTPException(422, "Invalid resource type or ID")
    record = db.get(MODELS[kind], resource_id)
    if record is None:
        raise HTTPException(404, "Knowledge record not found")
    return record


def _valid_evidence(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == 'https' and bool(parsed.hostname)
                and not parsed.username and not parsed.password
                and parsed.hostname.lower() not in ('localhost',))
    except ValueError:
        return False


def _dependencies_verified(db, kind, record):
    if kind == 'manufacturer':
        return True
    if kind == 'equipment_model':
        parent = db.get(Manufacturer, record.manufacturer_id)
        return bool(parent and parent.verification_status == 'verified')
    if kind == 'technical_document':
        equipment = db.get(EquipmentModel, record.equipment_model_id)
        return bool(equipment and _dependencies_verified(db, 'equipment_model', equipment)
                    and equipment.verification_status == 'verified')
    document = db.get(TechnicalDocument, record.source_document_id)
    return bool(document and document.equipment_model_id == record.equipment_model_id
                and document.verification_status == 'verified'
                and _dependencies_verified(db, 'technical_document', document))


def _audit(db, admin_id, action, kind, record, note, evidence_url=None):
    db.add(AuditLog(user_id=admin_id, action=action, resource_type=kind,
                    resource_id=record.id, details=json.dumps({
                        'note': note.strip(), 'evidence_url': evidence_url,
                        'new_status': record.verification_status,
                        'recorded_at': datetime.now(timezone.utc).isoformat(),
                    })))


def verify_manufacturer_knowledge(db: Session, resource_type: str, resource_id: int,
                                    admin_user_id: int, verification_note: str,
                                    evidence_url: str):
    record = _resource(db, resource_type, resource_id)
    if record.verification_status == 'verified':
        raise HTTPException(409, 'Already verified')
    if len(verification_note.strip()) < 10 or not _valid_evidence(evidence_url):
        raise HTTPException(422, 'A review note and HTTPS evidence URL are required')
    if not _dependencies_verified(db, resource_type, record):
        raise HTTPException(422, 'Parent manufacturer, equipment, and source document must be verified first')
    # For documents, require the recorded document URL to match the reviewed evidence URL.
    if resource_type == 'technical_document' and record.source_url.strip() != evidence_url.strip():
        raise HTTPException(422, 'Evidence URL must match the registered document URL')
    record.verification_status = 'verified'
    if resource_type == 'technical_document':
        record.last_verified = datetime.now(timezone.utc)
    _audit(db, admin_user_id, 'manufacturer_knowledge_verified', resource_type,
           record, verification_note, evidence_url)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return record


def revoke_manufacturer_knowledge(db: Session, resource_type: str, resource_id: int,
                                    admin_user_id: int, reason: str):
    record = _resource(db, resource_type, resource_id)
    if len(reason.strip()) < 10:
        raise HTTPException(422, 'Revocation reason must be at least 10 characters')
    # Descendant statuses are explicitly revoked, not merely filtered at query time.
    targets = []
    if resource_type == 'manufacturer':
        models = db.query(EquipmentModel).filter_by(manufacturer_id=record.id).all()
        for model in models:
            docs = db.query(TechnicalDocument).filter_by(equipment_model_id=model.id).all()
            faults = db.query(EquipmentFaultCode).filter_by(equipment_model_id=model.id).all()
            targets.extend([('fault_code', f) for f in faults])
            targets.extend([('technical_document', d) for d in docs])
            targets.append(('equipment_model', model))
    elif resource_type == 'equipment_model':
        targets.extend(('fault_code', f) for f in db.query(EquipmentFaultCode).filter_by(equipment_model_id=record.id).all())
        targets.extend(('technical_document', d) for d in db.query(TechnicalDocument).filter_by(equipment_model_id=record.id).all())
    elif resource_type == 'technical_document':
        targets.extend(('fault_code', f) for f in db.query(EquipmentFaultCode).filter_by(source_document_id=record.id).all())
    targets.append((resource_type, record))
    changed = 0
    for kind, item in targets:
        if item.verification_status != 'revoked':
            item.verification_status = 'revoked'
            if kind == 'technical_document':
                item.last_verified = None
            _audit(db, admin_user_id, 'manufacturer_knowledge_revoked', kind, item, reason)
            changed += 1
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'resource_type': resource_type, 'resource_id': resource_id,
            'verification_status': 'revoked', 'records_revoked': changed}


def trusted_fault_codes(db: Session, equipment_model_id: int, fault_code: str | None = None):
    """Fail closed: return only fault codes whose full evidence chain is verified."""
    query = (db.query(EquipmentFaultCode)
             .join(TechnicalDocument, EquipmentFaultCode.source_document_id == TechnicalDocument.id)
             .join(EquipmentModel, EquipmentFaultCode.equipment_model_id == EquipmentModel.id)
             .join(Manufacturer, EquipmentModel.manufacturer_id == Manufacturer.id)
             .filter(EquipmentFaultCode.equipment_model_id == equipment_model_id,
                     EquipmentFaultCode.verification_status == 'verified',
                     TechnicalDocument.verification_status == 'verified',
                     EquipmentModel.verification_status == 'verified',
                     Manufacturer.verification_status == 'verified',
                     TechnicalDocument.equipment_model_id == EquipmentFaultCode.equipment_model_id))
    if fault_code is not None:
        query = query.filter(EquipmentFaultCode.fault_code == fault_code)
    return query.order_by(EquipmentFaultCode.id).limit(200).all()
