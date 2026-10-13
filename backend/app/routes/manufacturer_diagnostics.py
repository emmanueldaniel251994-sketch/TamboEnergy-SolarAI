"""Authenticated source-grounded manufacturer diagnostic API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.services.manufacturer_grounding import grounded_diagnostic

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


class ManufacturerDiagnosticRequest(BaseModel):
    equipment_model_id: int = Field(gt=0)
    fault_code: str = Field(min_length=1, max_length=100)

    @field_validator("fault_code")
    @classmethod
    def nonempty_code(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Fault code must not be blank")
        return value


@router.post("/manufacturer-diagnostic")
def manufacturer_diagnostic(
    data: ManufacturerDiagnosticRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    result = grounded_diagnostic(db, data.equipment_model_id, data.fault_code)
    if result is None:
        raise HTTPException(status_code=404, detail="Equipment model not found")
    return result
