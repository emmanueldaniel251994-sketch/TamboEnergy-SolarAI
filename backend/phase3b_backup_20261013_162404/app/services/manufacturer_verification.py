
"""Controlled manufacturer knowledge verification service."""

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.manufacturer_knowledge import (
    Manufacturer,
    EquipmentModel,
    TechnicalDocument,
    EquipmentFaultCode,
)


MODEL_TYPES = {
    "manufacturer": Manufacturer,
    "equipment_model": EquipmentModel,
    "technical_document": TechnicalDocument,
    "fault_code": EquipmentFaultCode,
}


def verify_manufacturer_knowledge(
    db: Session,
    resource_type: str,
    resource_id: int,
    admin_user_id: int,
    verification_note: str,
):
    """Verify a record after an administrator reviews its evidence."""

    if resource_type not in MODEL_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported knowledge resource type",
        )

    if not verification_note or len(verification_note.strip()) < 10:
        raise HTTPException(
            status_code=422,
            detail="A verification note of at least 10 characters is required",
        )

    model_class = MODEL_TYPES[resource_type]
    record = db.get(model_class, resource_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge record not found",
        )

    if record.verification_status == "verified":
        raise HTTPException(
            status_code=409,
            detail="Knowledge record is already verified",
        )

    if resource_type == "equipment_model":
        manufacturer = db.get(
            Manufacturer,
            record.manufacturer_id,
        )

        if not manufacturer or manufacturer.verification_status != "verified":
            raise HTTPException(
                status_code=422,
                detail="Manufacturer must be verified first",
            )

    elif resource_type == "technical_document":
        equipment = db.get(
            EquipmentModel,
            record.equipment_model_id,
        )

        if not equipment or equipment.verification_status != "verified":
            raise HTTPException(
                status_code=422,
                detail="Equipment model must be verified first",
            )

    elif resource_type == "fault_code":
        equipment = db.get(
            EquipmentModel,
            record.equipment_model_id,
        )
        document = db.get(
            TechnicalDocument,
            record.source_document_id,
        )

        if not equipment or equipment.verification_status != "verified":
            raise HTTPException(
                status_code=422,
                detail="Equipment model must be verified first",
            )

        if (
            not document
            or document.equipment_model_id != record.equipment_model_id
            or document.verification_status != "verified"
        ):
            raise HTTPException(
                status_code=422,
                detail="Matching source document must be verified first",
            )

    record.verification_status = "verified"

    if resource_type == "technical_document":
        from datetime import datetime, timezone
        record.last_verified = datetime.now(timezone.utc)

    audit = AuditLog(
        user_id=admin_user_id,
        action="manufacturer_knowledge_verified",
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps({
            "verification_note": verification_note.strip(),
            "previous_status": "pending",
            "new_status": "verified",
        }),
    )

    db.add(audit)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(record)

    return record
