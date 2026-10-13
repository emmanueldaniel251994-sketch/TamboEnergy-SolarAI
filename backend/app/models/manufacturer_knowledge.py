
"""Manufacturer knowledge base models for Phase 3A."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, JSON,
    String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True)
    official_website = Column(String(500))
    verification_status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    equipment_models = relationship("EquipmentModel", back_populates="manufacturer")


class EquipmentModel(Base):
    __tablename__ = "equipment_models"

    id = Column(Integer, primary_key=True)
    manufacturer_id = Column(
        Integer, ForeignKey("manufacturers.id"), nullable=False
    )
    model_name = Column(String(200), nullable=False)
    equipment_type = Column(String(100), nullable=False)
    technical_specs = Column(JSON, nullable=False, default=dict)
    verification_status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    manufacturer = relationship("Manufacturer", back_populates="equipment_models")
    documents = relationship("TechnicalDocument", back_populates="equipment_model")
    fault_codes = relationship("EquipmentFaultCode", back_populates="equipment_model")

    __table_args__ = (
        UniqueConstraint(
            "manufacturer_id", "model_name", "equipment_type",
            name="uq_manufacturer_equipment_model"
        ),
    )


class TechnicalDocument(Base):
    __tablename__ = "technical_documents"

    id = Column(Integer, primary_key=True)
    equipment_model_id = Column(
        Integer, ForeignKey("equipment_models.id"), nullable=False
    )
    title = Column(String(300), nullable=False)
    document_type = Column(String(100), nullable=False)
    source_url = Column(String(1000), nullable=False)
    document_version = Column(String(100))
    verification_status = Column(String(30), nullable=False, default="pending")
    last_verified = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    equipment_model = relationship("EquipmentModel", back_populates="documents")
    fault_codes = relationship("EquipmentFaultCode", back_populates="source_document")


class EquipmentFaultCode(Base):
    __tablename__ = "equipment_fault_codes"

    id = Column(Integer, primary_key=True)
    equipment_model_id = Column(
        Integer, ForeignKey("equipment_models.id"), nullable=False
    )
    source_document_id = Column(
        Integer, ForeignKey("technical_documents.id"), nullable=False
    )
    fault_code = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(30), nullable=False, default="unknown")
    recommended_action = Column(Text)
    verification_status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    equipment_model = relationship("EquipmentModel", back_populates="fault_codes")
    source_document = relationship("TechnicalDocument", back_populates="fault_codes")

    __table_args__ = (
        UniqueConstraint(
            "equipment_model_id", "fault_code",
            name="uq_equipment_model_fault_code"
        ),
    )