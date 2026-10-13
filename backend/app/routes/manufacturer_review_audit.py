"""Admin-only read-only review readiness report."""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import require_roles
from app.services.manufacturer_pdf_reviews_db import review_audit, DecisionError

router = APIRouter(prefix='/manufacturer-knowledge', tags=['Manufacturer Knowledge'])

@router.get('/documents/pending-review/{sha256}/audit')
def review_audit_route(sha256: str, db: Session = Depends(get_db), admin=Depends(require_roles('admin'))):
    folder = os.environ.get('SOLARAI_PENDING_PDF_DIR')
    if not folder:
        raise HTTPException(503, 'SOLARAI_PENDING_PDF_DIR is not configured')
    try:
        return review_audit(db, folder, sha256)
    except (DecisionError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
