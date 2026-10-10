from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.telemetry import Telemetry
from app.models.solar_system import SolarSystem
from app.models.user import User
from app.security import get_current_user
from app.services.diagnostic_service import generate_diagnostic
from app.services.ai_assistant import explain

router=APIRouter(prefix="/ai-assistant",tags=["AI Assistant"])
class AskRequest(BaseModel):
    question:str=Field(min_length=5,max_length=2000)
    telemetry_id:int|None=Field(default=None,gt=0)

@router.post("/ask")
def ask(data:AskRequest,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    diagnosis=None
    if data.telemetry_id is not None:
        t=db.query(Telemetry).filter(Telemetry.id==data.telemetry_id).first()
        if not t: raise HTTPException(404,"Telemetry not found")
        system=db.query(SolarSystem).filter(SolarSystem.id==t.solar_system_id).first()
        if not system: raise HTTPException(404,"Solar system not found")
        if user.role=="customer" and (user.customer_id is None or user.customer_id!=system.customer_id):
            raise HTTPException(403,"Access denied")
        diagnosis=generate_diagnostic(t.final_diagnosis or t.fault_type or "normal",
             t.fault_severity,t.ml_confidence,t.needs_review)
    return {"response":explain(data.question,diagnosis),"telemetry_id":data.telemetry_id}
