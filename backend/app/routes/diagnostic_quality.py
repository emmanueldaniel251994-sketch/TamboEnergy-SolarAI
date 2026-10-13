"""Authenticated quality-checked diagnostic endpoint; additive to existing routes."""
from fastapi import APIRouter, Depends
from app.security import get_current_user
from app.diagnostics.engine import DiagnosticRequest
from app.diagnostics.quality_gate import QualityReview, diagnose_checked

router = APIRouter(prefix='/ai-assistant', tags=['AI Assistant'])

@router.post('/diagnose-checked', response_model=QualityReview)
def diagnose_with_quality_gate(request: DiagnosticRequest, _user=Depends(get_current_user)):
    return diagnose_checked(request)
