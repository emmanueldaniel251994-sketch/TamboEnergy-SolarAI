from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    solar_system_id = Column(
        Integer,
        ForeignKey("solar_systems.id"),
        nullable=False
    )

    issue = Column(
        Text,
        nullable=False
    )

    action_taken = Column(
        Text,
        nullable=True
    )

    status = Column(
        String,
        default="open"
    )

    technician = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    solar_system = relationship(
        "SolarSystem",
        back_populates="maintenance_records"
    )