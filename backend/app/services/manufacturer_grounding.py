"""Fail-closed, source-linked manufacturer fault-code diagnostic retrieval."""
from sqlalchemy.orm import Session
from app.models.manufacturer_knowledge import Manufacturer, EquipmentModel, TechnicalDocument
from app.services.manufacturer_verification import trusted_fault_codes

SAFETY = (
    "Advisory information only. Do not bypass protection or work on energized "
    "equipment. Consult a qualified solar technician."
)


def grounded_diagnostic(db: Session, equipment_model_id: int, fault_code: str):
    """Return a verified exact-code match or an explicit unverified response.

    No untrusted record content is sent to a language model or treated as verified.
    """
    model = db.get(EquipmentModel, equipment_model_id)
    if model is None:
        return None
    manufacturer = db.get(Manufacturer, model.manufacturer_id)
    code = fault_code.strip()
    if not code:
        raise ValueError("Fault code is required")
    faults = trusted_fault_codes(db, equipment_model_id, code)
    sources = []
    matches = []
    for fault in faults:
        doc = db.get(TechnicalDocument, fault.source_document_id)
        if not doc or doc.equipment_model_id != model.id:
            continue
        sources.append({
            "document_id": doc.id,
            "title": doc.title,
            "source_url": doc.source_url,
            "document_version": doc.document_version,
            "last_verified": doc.last_verified.isoformat() if doc.last_verified else None,
        })
        matches.append({
            "fault_code": fault.fault_code,
            "description": fault.description,
            "severity": fault.severity,
            "recommended_action": fault.recommended_action,
            "source_document_id": doc.id,
        })
    return {
        "equipment_model_id": model.id,
        "model_name": model.model_name,
        "manufacturer_name": manufacturer.name if manufacturer else None,
        "fault_code": code,
        "grounded": bool(matches),
        "verification_status": "verified" if matches else "no_verified_match",
        "answer": (
            "Verified manufacturer record found. Review the source and follow "
            "the manufacturer's safety instructions."
            if matches else
            "No verified manufacturer-specific explanation is available for "
            "this exact equipment model and fault code. Do not assume a meaning."
        ),
        "matches": matches,
        "sources": sources,
        "safety_notice": SAFETY,
    }
