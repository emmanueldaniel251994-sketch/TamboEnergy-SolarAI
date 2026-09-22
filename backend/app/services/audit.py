from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    details: str | None = None
):

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details
    )

    db.add(audit_log)

    # Do not commit here.
    # The route performs one final transaction.
    db.flush()

    return audit_log