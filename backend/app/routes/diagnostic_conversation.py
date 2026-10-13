"""Authenticated diagnostic follow-up endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from app.security import get_current_user
from app.diagnostics.conversation import ConversationRequest, ConversationResponse, converse

router = APIRouter(prefix='/ai-assistant', tags=['AI Assistant'])

@router.post('/conversation', response_model=ConversationResponse)
def conversation(data: ConversationRequest, user=Depends(get_current_user)):
    try:
        return converse(data)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
