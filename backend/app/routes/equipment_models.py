
"""Equipment model API for TamboEnergy SolarAI Phase 3A."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.manufacturer_knowledge import (
    Manufacturer,
    EquipmentModel,
)
from app.security import get_current_user, require_roles


router = APIRouter(
    prefix="/equipment-models",
    tags=["Manufacturer Knowledge"],
)


class EquipmentModelCreate(BaseModel):
    manufacturer_id: int = Field(gt=0)
    model_name: str = Field(min_length=2, max_length=200)
    equipment_type: str = Field(min_length=2, max_length=100)
    technical_specs: dict[str, Any] = Field(default_factory=dict)


class EquipmentModelResponse(BaseModel):
    id: int
    manufacturer_id: int
    model_name: str
    equipment_type: str
    technical_specs: dict[str, Any]
    verification_status: str

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=EquipmentModelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_equipment_model(
    data: EquipmentModelCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    manufacturer = db.get(Manufacturer, data.manufacturer_id)

    if manufacturer is None:
        raise HTTPException(
            status_code=404,
            detail="Manufacturer not found",
        )

    model_name = data.model_name.strip()
    equipment_type = data.equipment_type.strip()

    if len(model_name) < 2 or len(equipment_type) < 2:
        raise HTTPException(
            status_code=422,
            detail="Model name and equipment type must contain at least two characters",
        )

    existing = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.manufacturer_id == data.manufacturer_id,
            EquipmentModel.model_name == model_name,
            EquipmentModel.equipment_type == equipment_type,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Equipment model already exists",
        )

    equipment = EquipmentModel(
        manufacturer_id=data.manufacturer_id,
        model_name=model_name,
        equipment_type=equipment_type,
        technical_specs=data.technical_specs,
        verification_status="pending",
    )

    db.add(equipment)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Equipment model already exists or references invalid data",
        ) from exc

    db.refresh(equipment)
    return equipment


@router.get(
    "",
    response_model=list[EquipmentModelResponse],
)
def list_equipment_models(
    manufacturer_id: int | None = Query(default=None, gt=0),
    equipment_type: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(EquipmentModel)

    if manufacturer_id is not None:
        query = query.filter(
            EquipmentModel.manufacturer_id == manufacturer_id
        )

    if equipment_type:
        query = query.filter(
            EquipmentModel.equipment_type == equipment_type
        )

    return (
        query.order_by(EquipmentModel.id.desc())
        .limit(200)
        .all()
    )


@router.get(
    "/{model_id}",
    response_model=EquipmentModelResponse,
)
def get_equipment_model(
    model_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment = db.get(EquipmentModel, model_id)

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment model not found",
        )

    return equipment
