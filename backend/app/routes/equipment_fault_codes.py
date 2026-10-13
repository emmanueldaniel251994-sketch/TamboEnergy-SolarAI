
"""Equipment fault code registry for TamboEnergy SolarAI Phase 3A."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.manufacturer_knowledge import (
    EquipmentModel,
    TechnicalDocument,
    EquipmentFaultCode,
)
from app.security import get_current_user, require_roles


router = APIRouter(
    prefix="/equipment-fault-codes",
    tags=["Manufacturer Knowledge"],
)


class FaultCodeCreate(BaseModel):
    equipment_model_id: int = Field(gt=0)
    source_document_id: int = Field(gt=0)
    fault_code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=3, max_length=5000)
    severity: str = Field(default="unknown")
    recommended_action: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("fault_code", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        value = value.strip().lower()
        allowed = {"unknown", "info", "warning", "critical"}

        if value not in allowed:
            raise ValueError(
                "Severity must be unknown, info, warning, or critical"
            )
        return value


class FaultCodeResponse(BaseModel):
    id: int
    equipment_model_id: int
    source_document_id: int
    fault_code: str
    description: str
    severity: str
    recommended_action: str | None
    verification_status: str

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=FaultCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_fault_code(
    data: FaultCodeCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    equipment = db.get(EquipmentModel, data.equipment_model_id)

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment model not found",
        )

    document = db.get(
        TechnicalDocument,
        data.source_document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Source document not found",
        )

    if document.equipment_model_id != data.equipment_model_id:
        raise HTTPException(
            status_code=422,
            detail="Source document does not belong to this equipment model",
        )

    existing = (
        db.query(EquipmentFaultCode)
        .filter(
            EquipmentFaultCode.equipment_model_id
            == data.equipment_model_id,
            EquipmentFaultCode.fault_code == data.fault_code,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Fault code already exists for this equipment model",
        )

    fault = EquipmentFaultCode(
        equipment_model_id=data.equipment_model_id,
        source_document_id=data.source_document_id,
        fault_code=data.fault_code,
        description=data.description,
        severity=data.severity,
        recommended_action=data.recommended_action,
        verification_status="pending",
    )

    db.add(fault)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Fault code already exists or references invalid data",
        ) from exc

    db.refresh(fault)
    return fault


@router.get(
    "",
    response_model=list[FaultCodeResponse],
)
def list_fault_codes(
    equipment_model_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(EquipmentFaultCode)

    if equipment_model_id is not None:
        query = query.filter(
            EquipmentFaultCode.equipment_model_id == equipment_model_id
        )

    return (
        query.order_by(EquipmentFaultCode.id.desc())
        .limit(200)
        .all()
    )


@router.get(
    "/{fault_id}",
    response_model=FaultCodeResponse,
)
def get_fault_code(
    fault_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    fault = db.get(EquipmentFaultCode, fault_id)

    if fault is None:
        raise HTTPException(
            status_code=404,
            detail="Fault code not found",
        )

    return fault
