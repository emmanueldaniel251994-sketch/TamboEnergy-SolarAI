from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.audit_log import AuditLog
from app.models.user import User

from app.schemas.audit import (
    AuditLogResponse
)

from app.security import require_roles


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"]
)


# ============================================================
# GET AUDIT LOGS
# ADMIN ONLY
# ============================================================

@router.get(
    "/",
    response_model=list[
        AuditLogResponse
    ]
)
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    return (
        db.query(AuditLog)
        .order_by(
            AuditLog.created_at.desc()
        )
        .all()
    )