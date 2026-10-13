"""User-owned persisted diagnostic sessions; uses the existing quality-checked converse()."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.ai_conversation import AIConversationSession, AIConversationMessage
from app.diagnostics.conversation import ConversationRequest, converse
from app.diagnostics.equipment_profile import EquipmentProfile
from app.diagnostics.information_extractor import extract_equipment_updates
from app.services.session_manufacturer_evidence import attach_evidence


def _utc():
    return datetime.now(timezone.utc)


def get_owned(db: Session, user_id: int, session_id: int):
    return db.query(AIConversationSession).filter(
        AIConversationSession.id == session_id,
        AIConversationSession.user_id == user_id,
    ).first()


def run_turn(db: Session, session: AIConversationSession, question: str, updates: dict | None = None):
    # Profile validation occurs before writes; failed diagnosis leaves history unchanged.
    profile = EquipmentProfile.model_validate(session.equipment_profile)
  
    # Extract clearly identified measurements from the customer's message.
    extracted_updates = extract_equipment_updates(question)

    # Explicit API updates take priority over extracted values.
    merged_updates = {**extracted_updates, **(updates or {})}

    # Preserve the original complaint as diagnostic context.
    diagnostic_question = question
    if session.original_complaint and session.original_complaint.strip() != question.strip():
        diagnostic_question = (
            f"Original complaint: {session.original_complaint}\n"
            f"Latest customer message: {question}"
        )

    result = converse(
        ConversationRequest(
            question=diagnostic_question,
            profile=profile,
            updates=merged_updates,
        )
    )
    if result.profile.equipment_model_id:
        result = attach_evidence(db, result, diagnostic_question)

    # Preserve original symptom for short follow-up messages unless explicitly updated.
    session.equipment_profile = result.profile.model_dump(mode='json')
    session.updated_at = _utc()
    db.add(AIConversationMessage(session_id=session.id, role='user', content=question))
    db.add(AIConversationMessage(session_id=session.id, role='assistant', content=result.message,
        response_metadata=result.model_dump(mode='json')))
    db.commit()
    db.refresh(session)
    return result
