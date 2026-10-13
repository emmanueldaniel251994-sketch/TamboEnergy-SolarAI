"""Authenticated, stateless conversational solar diagnostics endpoint."""
from fastapi import APIRouter, Depends
from app.security import get_current_user
from app.diagnostics.engine import DiagnosticRequest, DiagnosticResult, diagnose

router = APIRouter(prefix='/ai-assistant', tags=['AI Assistant'])


@router.post('/diagnose', response_model=DiagnosticResult)
def universal_diagnose(data: DiagnosticRequest, user=Depends(get_current_user)):
    # Authenticated endpoint. No cross-customer telemetry is loaded here.
    # The caller submits only its own current equipment profile.
    return diagnose(data)
