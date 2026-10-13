"""Persisted, user-owned SolarAI diagnostic conversations."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AIConversationSession(Base):
    __tablename__ = "ai_conversation_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    original_complaint = Column(Text, nullable=False)
    equipment_profile = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    messages = relationship("AIConversationMessage", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)


class AIConversationMessage(Base):
    __tablename__ = "ai_conversation_messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("ai_conversation_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)  # 'user' or 'assistant'; validate at API layer
    content = Column(Text, nullable=False)
    response_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    session = relationship("AIConversationSession", back_populates="messages")
    __table_args__ = (Index("ix_ai_conversation_messages_session_id_id", "session_id", "id"),)
