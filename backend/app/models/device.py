from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    solar_system_id = Column(
        Integer,
        ForeignKey(
            "solar_systems.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    device_name = Column(
        String(150),
        nullable=False,
    )

    device_type = Column(
        String(100),
        nullable=False,
        default="monitoring_gateway",
    )

    manufacturer = Column(
        String(150),
        nullable=True,
    )

    model = Column(
        String(150),
        nullable=True,
    )

    serial_number = Column(
        String(150),
        unique=True,
        nullable=True,
        index=True,
    )

    # Store only a hash of the API key.
    # Never store the raw device credential.
    api_key_hash = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    last_seen = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(
            timezone.utc
        ),
    )

    solar_system = relationship(
        "SolarSystem",
    )

    telemetry_records = relationship(
        "Telemetry",
        back_populates="device",
        passive_deletes=True,
    )