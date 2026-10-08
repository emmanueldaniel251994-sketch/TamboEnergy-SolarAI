from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "device_event_id",
            name="uq_telemetry_device_event",
        ),
    )

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

    # Device provenance is optional because telemetry may also
    # be created manually by an authenticated technician.
    device_id = Column(
        Integer,
        ForeignKey(
            "devices.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Optional gateway-generated event identifier. Together with device_id
    # it provides idempotency for retries after network interruptions.
    device_event_id = Column(
        String(100),
        nullable=True,
        index=True,
    )

    # Timestamp supplied by a signed device request. This is separate from
    # created_at, which records when SolarAI persisted the telemetry.
    device_timestamp = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # ========================================================
    # SOLAR / BATTERY SENSOR DATA
    # ========================================================

    pv_voltage = Column(
        Float,
        nullable=True,
    )

    pv_current = Column(
        Float,
        nullable=True,
    )

    pv_power = Column(
        Float,
        nullable=True,
    )

    battery_voltage = Column(
        Float,
        nullable=True,
    )

    battery_current = Column(
        Float,
        nullable=True,
    )

    battery_soc = Column(
        Float,
        nullable=True,
    )

    load_power = Column(
        Float,
        nullable=True,
    )

    temperature = Column(
        Float,
        nullable=True,
    )

    error_code = Column(
        String,
        nullable=True,
    )

    # ========================================================
    # RULE ENGINE
    # ========================================================

    fault_type = Column(
        String,
        nullable=True,
    )

    fault_severity = Column(
        String,
        nullable=True,
    )

    # ========================================================
    # MACHINE LEARNING
    # ========================================================

    ml_prediction = Column(
        String,
        nullable=True,
    )

    ml_confidence = Column(
        Float,
        nullable=True,
    )

    ml_prediction_available = Column(
        Integer,
        default=1,
        nullable=False,
    )

    # ========================================================
    # DATA QUALITY
    # ========================================================

    data_quality_score = Column(
        Float,
        default=100.0,
        nullable=False,
    )

    missing_fields = Column(
        Text,
        nullable=True,
    )

    # ========================================================
    # FINAL DIAGNOSIS
    # ========================================================

    prediction_agreement = Column(
        String,
        nullable=True,
    )

    final_diagnosis = Column(
        String,
        nullable=True,
    )

    needs_review = Column(
        Integer,
        default=0,
        nullable=False,
    )

    status = Column(
        String,
        default="normal",
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
        index=True,
    )

    solar_system = relationship(
        "SolarSystem"
    )

    device = relationship(
        "Device",
        back_populates="telemetry_records",
    )