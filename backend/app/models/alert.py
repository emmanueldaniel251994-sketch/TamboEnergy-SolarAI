from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    # --------------------------------------------------------
    # PRIMARY KEY
    # --------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # --------------------------------------------------------
    # RELATED SOLAR SYSTEM
    # --------------------------------------------------------

    solar_system_id = Column(
        Integer,
        ForeignKey(
            "solar_systems.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # RELATED TELEMETRY RECORD
    # --------------------------------------------------------

    telemetry_id = Column(
        Integer,
        ForeignKey(
            "telemetry.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    # --------------------------------------------------------
    # ALERT INFORMATION
    # --------------------------------------------------------

    alert_type = Column(
        String,
        nullable=False,
        index=True,
    )

    severity = Column(
        String,
        nullable=False,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    # --------------------------------------------------------
    # ALERT STATUS
    #
    # open
    # acknowledged
    # resolved
    # --------------------------------------------------------

    status = Column(
        String,
        default="open",
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # TECHNICIAN REVIEW
    # --------------------------------------------------------

    needs_review = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    solar_system = relationship(
        "SolarSystem"
    )

    telemetry = relationship(
        "Telemetry"
    )