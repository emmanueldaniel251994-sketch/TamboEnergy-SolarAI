"""Admin-only read-only pending PDF provenance and integrity review."""
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from app.security import require_roles
from app.services.manufacturer_pdf_review import ReviewError, review_inventory, review_one

router = APIRouter(prefix='/manufacturer-knowledge', tags=['Manufacturer Knowledge'])

def configured_dir():
    path = os.environ.get('SOLARAI_PENDING_PDF_DIR')
    if not path:
        raise HTTPException(503, 'SOLARAI_PENDING_PDF_DIR is not configured')
    return path

@router.get('/documents/pending-review')
def pending_review(limit: int = Query(default=50, ge=1, le=100),
                   admin=Depends(require_roles('admin'))):
    return review_inventory(configured_dir(), limit)

@router.get('/documents/pending-review/{sha256}')
def pending_review_detail(sha256: str, admin=Depends(require_roles('admin'))):
    try:
        return review_one(configured_dir(), sha256)
    except ReviewError as exc:
        raise HTTPException(404 if str(exc) == 'Pending document not found' else 422, str(exc)) from exc
