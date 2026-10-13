"""Authenticated manufacturer-grounded question endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.services.manufacturer_chat import answer_manufacturer_question

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])

class ManufacturerAskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    equipment_model_id: int = Field(gt=0)
    fault_code: str = Field(min_length=1, max_length=100)

    @field_validator("question", "fault_code")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

@router.post("/manufacturer-ask")
def manufacturer_ask(data: ManufacturerAskRequest,
                     db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    result = answer_manufacturer_question(
        db, data.question, data.equipment_model_id, data.fault_code
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Equipment model not found")
    return result
