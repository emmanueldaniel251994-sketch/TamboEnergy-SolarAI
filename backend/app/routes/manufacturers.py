
"""Manufacturer registry API for TamboEnergy SolarAI Phase 3A."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.manufacturer_knowledge import Manufacturer
from app.security import get_current_user, require_roles


router = APIRouter(
    prefix="/manufacturers",
    tags=["Manufacturer Knowledge"],
)


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    official_website: str | None = Field(default=None, max_length=500)


class ManufacturerResponse(BaseModel):
    id: int
    name: str
    official_website: str | None
    verification_status: str

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=ManufacturerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manufacturer(
    data: ManufacturerCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    name = data.name.strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Manufacturer name is too short",
        )

    existing = db.query(Manufacturer).filter(
        Manufacturer.name == name
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Manufacturer already exists",
        )

    manufacturer = Manufacturer(
        name=name,
        official_website=data.official_website,
        verification_status="pending",
    )

    db.add(manufacturer)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Manufacturer already exists",
        ) from exc

    db.refresh(manufacturer)
    return manufacturer


@router.get("", response_model=list[ManufacturerResponse])
def list_manufacturers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return (
        db.query(Manufacturer)
        .order_by(Manufacturer.name.asc())
        .limit(200)
        .all()
    )


@router.get("/{manufacturer_id}", response_model=ManufacturerResponse)
def get_manufacturer(
    manufacturer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    manufacturer = db.get(Manufacturer, manufacturer_id)

    if manufacturer is None:
        raise HTTPException(
            status_code=404,
            detail="Manufacturer not found",
        )

    return manufacturer
