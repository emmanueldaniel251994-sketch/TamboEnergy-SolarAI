from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class SolarSystem(Base):
    __tablename__ = "solar_systems"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    inverter_brand = Column(
        String,
        nullable=True
    )

    inverter_capacity_kva = Column(
        Float,
        nullable=True
    )

    battery_type = Column(
        String,
        nullable=True
    )

    battery_capacity_kwh = Column(
        Float,
        nullable=True
    )

    panel_count = Column(
        Integer,
        nullable=True
    )

    panel_wattage = Column(
        Float,
        nullable=True
    )

    location = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    customer = relationship(
        "Customer",
        back_populates="solar_systems"
    )

    maintenance_records = relationship(
        "MaintenanceRecord",
        back_populates="solar_system",
        cascade="all, delete-orphan"
    )