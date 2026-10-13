"""Admin review and trusted manufacturer fault lookup."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user, require_roles
from app.services.manufacturer_verification import (verify_manufacturer_knowledge,
    revoke_manufacturer_knowledge, trusted_fault_codes)

router = APIRouter(prefix='/manufacturer-knowledge', tags=['Manufacturer Knowledge Verification'])

class VerifyRequest(BaseModel):
    verification_note: str = Field(min_length=10, max_length=2000)
    evidence_url: str = Field(min_length=12, max_length=1000)

class RevokeRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)

class TrustedFaultResponse(BaseModel):
    id: int
    equipment_model_id: int
    source_document_id: int
    fault_code: str
    description: str
    severity: str
    recommended_action: str | None
    verification_status: str
    model_config = ConfigDict(from_attributes=True)

@router.post('/{resource_type}/{resource_id}/verify')
def verify_record(resource_type: str, resource_id: int, data: VerifyRequest,
                  db: Session = Depends(get_db), admin=Depends(require_roles('admin'))):
    record = verify_manufacturer_knowledge(db, resource_type, resource_id,
                                           admin.id, data.verification_note, data.evidence_url)
    return {'resource_type': resource_type, 'resource_id': record.id,
            'verification_status': record.verification_status}

@router.post('/{resource_type}/{resource_id}/revoke')
def revoke_record(resource_type: str, resource_id: int, data: RevokeRequest,
                  db: Session = Depends(get_db), admin=Depends(require_roles('admin'))):
    return revoke_manufacturer_knowledge(db, resource_type, resource_id, admin.id, data.reason)

@router.get('/trusted-fault-codes/{equipment_model_id}', response_model=list[TrustedFaultResponse])
def list_trusted_faults(equipment_model_id: int, fault_code: str | None = Query(None, max_length=100),
                       db: Session = Depends(get_db), user=Depends(get_current_user)):
    if equipment_model_id < 1:
        raise HTTPException(422, 'Invalid equipment model ID')
    return trusted_fault_codes(db, equipment_model_id, fault_code)
