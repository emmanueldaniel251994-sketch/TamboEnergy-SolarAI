from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class DeviceRequestNonce(Base):
    __tablename__ = "device_request_nonces"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "nonce",
            name="uq_device_request_nonce_device_nonce",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nonce = Column(String(128), nullable=False)
    request_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
