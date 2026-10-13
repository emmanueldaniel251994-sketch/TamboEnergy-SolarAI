"""Administrator-only PDF provenance review journal."""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.security import require_roles
from app.services.manufacturer_review_decisions import record_decision, decision_history, DecisionError

router = APIRouter(prefix="/manufacturer-knowledge", tags=["Manufacturer Knowledge"])

class ReviewDecision(BaseModel):
    decision: str = Field(pattern="^(approve_provenance|reject|needs_more_evidence)$")
    evidence_url: str | None = Field(default=None, max_length=2048)
    note: str = Field(min_length=20, max_length=2000)

def configured_dir():
    directory = os.environ.get("SOLARAI_PENDING_PDF_DIR")
    if not directory:
        raise HTTPException(503, "SOLARAI_PENDING_PDF_DIR is not configured")
    return directory

@router.post("/documents/pending-review/{sha256}/decision")
def submit_review(sha256: str, body: ReviewDecision, admin=Depends(require_roles("admin"))):
    try:
        return record_decision(configured_dir(), sha256, body.decision, admin.id,
                               body.evidence_url, body.note)
    except DecisionError as exc:
        raise HTTPException(422, str(exc)) from exc

@router.get("/documents/pending-review/{sha256}/decisions")
def list_decisions(sha256: str, admin=Depends(require_roles("admin"))):
    try:
        return {"decisions": decision_history(configured_dir(), sha256)}
    except DecisionError as exc:
        raise HTTPException(422, str(exc)) from exc
