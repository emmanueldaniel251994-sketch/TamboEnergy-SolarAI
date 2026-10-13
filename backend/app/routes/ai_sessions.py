"""Authenticated conversation sessions, separate from legacy stateless endpoint."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user
from app.diagnostics.equipment_profile import EquipmentProfile
from app.diagnostics.conversation import ConversationResponse
from app.models.ai_conversation import AIConversationSession, AIConversationMessage
from app.services.ai_sessions import get_owned, run_turn
from app.services.session_manufacturer_evidence import attach_evidence, refresh_stored_evidence

router = APIRouter(prefix='/ai-assistant/sessions', tags=['AI Assistant'])

class StartSession(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    profile: EquipmentProfile = Field(default_factory=EquipmentProfile)

class ContinueSession(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    updates: dict[str, Any] = Field(default_factory=dict)

class SessionSummary(BaseModel):
    id: int
    title: str
    original_complaint: str
    equipment_profile: dict[str, Any]
    model_config = {'from_attributes': True}

class TurnResponse(BaseModel):
    session_id: int
    response: ConversationResponse

class MessageView(BaseModel):
    id: int
    role: str
    content: str
    response_metadata: dict[str, Any] | None = None
    model_config = {'from_attributes': True}

class SessionDetail(BaseModel):
    session: SessionSummary
    messages: list[MessageView]

@router.post('', response_model=TurnResponse, status_code=201)
def create_session(data: StartSession, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Diagnose first to avoid persisting empty sessions on validation/engine failures.
    from app.diagnostics.conversation import ConversationRequest, converse
    try:
        result = converse(ConversationRequest(question=data.question, profile=data.profile))
        result = attach_evidence(db, result, data.question)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session = AIConversationSession(user_id=user.id, title=data.question[:200],
        original_complaint=data.question, equipment_profile=result.profile.model_dump(mode='json'))
    db.add(session)
    db.flush()
    db.add_all([
        AIConversationMessage(session_id=session.id, role='user', content=data.question),
        AIConversationMessage(session_id=session.id, role='assistant', content=result.message,
            response_metadata=result.model_dump(mode='json')),
    ])
    db.commit()
    db.refresh(session)
    return TurnResponse(session_id=session.id, response=result)

@router.get('', response_model=list[SessionSummary])
def list_sessions(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(AIConversationSession).filter(AIConversationSession.user_id == user.id).order_by(
        AIConversationSession.updated_at.desc(), AIConversationSession.id.desc()).limit(100).all()

@router.get('/{session_id}', response_model=SessionDetail)
def retrieve_session(session_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session = get_owned(db, user.id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Conversation not found')
    messages = db.query(AIConversationMessage).filter(AIConversationMessage.session_id == session.id).order_by(
        AIConversationMessage.id.asc()).limit(500).all()
    cache = {}
    views = []
    for row in messages:
        view = MessageView.model_validate(row)
        if view.role == 'assistant':
            view.response_metadata = refresh_stored_evidence(db, view.response_metadata, cache)
        views.append(view)
    return SessionDetail(session=session, messages=views)

@router.post('/{session_id}/messages', response_model=TurnResponse)
def continue_session(session_id: int, data: ContinueSession, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session = get_owned(db, user.id, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Conversation not found')
    try:
        result = run_turn(db, session, data.question, data.updates)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TurnResponse(session_id=session.id, response=result)
