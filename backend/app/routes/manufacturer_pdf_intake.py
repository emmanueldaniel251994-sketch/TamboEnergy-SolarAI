"""Admin-only local PDF intake, intentionally no auto-approval."""
import base64
import binascii
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.manufacturer_knowledge import EquipmentModel
from app.security import require_roles
from app.services.manufacturer_pdf_intake import (
    PdfIntakeError, PdfIntakeBusyError, MAX_PDF_BYTES, inspect_pdf, save_pending_pdf,
)
from app.services.manufacturer_document_intake import valid_source_url

router = APIRouter(prefix='/manufacturer-knowledge', tags=['Manufacturer Knowledge'])

class PdfIntakeRequest(BaseModel):
    equipment_model_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=250)
    source_url: str = Field(min_length=12, max_length=2048)
    pdf_base64: str = Field(min_length=8, max_length=11_200_000)
    commit: bool = False

@router.post('/documents/pdf-intake')
def pdf_intake(payload: PdfIntakeRequest, db: Session = Depends(get_db),
               admin=Depends(require_roles('admin'))):
    if os.environ.get('APP_ENV', '').strip().lower() == 'production' and os.environ.get(
        'SOLARAI_PDF_INTAKE_ENABLED', ''
    ).strip().lower() not in {'1', 'true', 'yes', 'on'}:
        raise HTTPException(503, 'PDF intake is disabled pending deployment isolation review')
    if not db.get(EquipmentModel, payload.equipment_model_id):
        raise HTTPException(404, 'Equipment model not found')
    if not valid_source_url(payload.source_url):
        raise HTTPException(422, 'A valid HTTPS source URL is required')
    try:
        data = base64.b64decode(payload.pdf_base64, validate=True)
        if len(data) > MAX_PDF_BYTES:
            raise PdfIntakeError('PDF exceeds 8 MiB')
        report = inspect_pdf(data)
        summary = {key: value for key, value in report.items() if key != 'text'}
        if not payload.commit:
            return {'committed': False, **summary}
        storage = os.environ.get('SOLARAI_PENDING_PDF_DIR')
        if not storage:
            raise HTTPException(503, 'SOLARAI_PENDING_PDF_DIR is not configured')
        metadata = save_pending_pdf(data, report, payload.equipment_model_id,
                                    payload.title.strip(), payload.source_url, storage)
        return {'committed': True, **metadata}
    except PdfIntakeBusyError as exc:
        raise HTTPException(503, str(exc), headers={'Retry-After': '10'}) from exc
    except (binascii.Error, PdfIntakeError) as exc:
        raise HTTPException(422, str(exc)) from exc
