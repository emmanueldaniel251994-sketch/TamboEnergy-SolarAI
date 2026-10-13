
"""Admin-only manufacturer knowledge verification API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_roles
from app.services.manufacturer_verification import (
    verify_manufacturer_knowledge,
)


router = APIRouter(
    prefix="/manufacturer-knowledge",
    tags=["Manufacturer Knowledge Verification"],
)


class VerificationRequest(BaseModel):
    verification_note: str = Field(
        min_length=10,
        max_length=2000,
    )


@router.post("/{resource_type}/{resource_id}/verify")
def verify_knowledge_record(
    resource_type: str,
    resource_id: int,
    data: VerificationRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("admin")),
):
    if resource_id <= 0:
        raise HTTPException(
            status_code=422,
            detail="Resource ID must be positive",
        )

    record = verify_manufacturer_knowledge(
        db=db,
        resource_type=resource_type,
        resource_id=resource_id,
        admin_user_id=admin.id,
        verification_note=data.verification_note,
    )

    return {
        "message": "Knowledge record verified successfully",
        "resource_type": resource_type,
        "resource_id": record.id,
        "verification_status": record.verification_status,
    }
