"""Admin-only document metadata manifest intake; no network fetch."""
import base64
import binascii
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import require_roles
from app.services.manufacturer_document_intake import (
    parse_manifest, prepare_manifest, commit_pending_documents, MAX_BYTES,
)

router = APIRouter(prefix="/manufacturer-knowledge", tags=["Manufacturer Knowledge"])

class DocumentManifestRequest(BaseModel):
    format: str = Field(pattern="^(csv|json)$")
    content_base64: str = Field(min_length=1, max_length=700000)
    commit: bool = False

@router.post("/documents/import")
def import_document_manifest(data: DocumentManifestRequest, db: Session = Depends(get_db),
                             admin=Depends(require_roles("admin"))):
    try:
        payload = base64.b64decode(data.content_base64, validate=True)
        if len(payload) > MAX_BYTES:
            raise ValueError("Manifest too large")
        report = prepare_manifest(db, parse_manifest(payload, data.format))
        if data.commit:
            if report["rejected"]:
                raise HTTPException(status_code=422, detail={"message": "Rejected rows; no changes made", "report": report})
            inserted = commit_pending_documents(db, report)
        else:
            inserted = 0
        return {"committed": data.commit, "inserted": inserted, **report}
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
