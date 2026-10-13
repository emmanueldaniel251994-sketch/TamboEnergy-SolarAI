
"""Technical document registry for TamboEnergy SolarAI Phase 3A."""

from datetime import datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.manufacturer_knowledge import (
    EquipmentModel,
    TechnicalDocument,
)
from app.security import get_current_user, require_roles


router = APIRouter(
    prefix="/technical-documents",
    tags=["Manufacturer Knowledge"],
)


class TechnicalDocumentCreate(BaseModel):
    equipment_model_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=300)
    document_type: str = Field(min_length=2, max_length=100)
    source_url: str = Field(min_length=10, max_length=1000)
    document_version: str | None = Field(default=None, max_length=100)

    @field_validator("title", "document_type")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Must contain at least two characters")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)

        if (
            parsed.scheme not in ("https", "http")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("A valid HTTP or HTTPS document URL is required")

        return value


class TechnicalDocumentResponse(BaseModel):
    id: int
    equipment_model_id: int
    title: str
    document_type: str
    source_url: str
    document_version: str | None
    verification_status: str
    last_verified: datetime | None

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=TechnicalDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_technical_document(
    data: TechnicalDocumentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    equipment = db.get(EquipmentModel, data.equipment_model_id)

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment model not found",
        )

    document = TechnicalDocument(
        equipment_model_id=data.equipment_model_id,
        title=data.title,
        document_type=data.document_type,
        source_url=data.source_url,
        document_version=data.document_version,
        verification_status="pending",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get(
    "",
    response_model=list[TechnicalDocumentResponse],
)
def list_technical_documents(
    equipment_model_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(TechnicalDocument)

    if equipment_model_id is not None:
        query = query.filter(
            TechnicalDocument.equipment_model_id == equipment_model_id
        )

    return (
        query.order_by(TechnicalDocument.id.desc())
        .limit(200)
        .all()
    )


@router.get(
    "/{document_id}",
    response_model=TechnicalDocumentResponse,
)
def get_technical_document(
    document_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    document = db.get(TechnicalDocument, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Technical document not found",
        )

    return document
