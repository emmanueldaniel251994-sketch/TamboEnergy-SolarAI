"""Persistent provenance reviews; independent of manufacturer verification."""
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from app.database import Base


class ManufacturerPDFReview(Base):
    __tablename__ = 'manufacturer_pdf_reviews'
    __table_args__ = (
        CheckConstraint("decision IN ('approve_provenance','reject','needs_more_evidence')", name='ck_pdf_review_decision'),
        Index('ix_pdf_review_sha_id', 'sha256', 'id'),
    )
    id = Column(Integer, primary_key=True)
    sha256 = Column(String(64), nullable=False)
    decision = Column(String(32), nullable=False)
    reviewer_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reviewer_reference = Column(String(120), nullable=False)
    evidence_url = Column(String(2048), nullable=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    legacy_key = Column(String(64), unique=True, nullable=True)
