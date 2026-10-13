"""Admin-only manufacturer fault import: preview or commit pending records."""
import base64
import binascii
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import require_roles
from app.services.manufacturer_import import parse_import, prepare_import, import_pending

router = APIRouter(prefix='/manufacturer-knowledge', tags=['Manufacturer Knowledge Import'])

class ImportRequest(BaseModel):
    format: str = Field(pattern='^(csv|json)$')
    content_base64: str = Field(min_length=1, max_length=700000)
    commit: bool = False

@router.post('/fault-codes/import')
def import_fault_codes(data: ImportRequest, db: Session = Depends(get_db), admin=Depends(require_roles('admin'))):
    try:
        raw = base64.b64decode(data.content_base64, validate=True)
        rows = parse_import(raw, data.format)
        report = prepare_import(db, rows)
        imported = import_pending(db, report) if data.commit else 0
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {'preview': not data.commit, 'accepted_count': len(report['accepted']),
            'rejected': report['rejected'], 'skipped': report['skipped'],
            'imported_count': imported, 'verification_status': 'pending'}
