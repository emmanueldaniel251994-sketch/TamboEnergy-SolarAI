from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.alert import Alert
from app.models.solar_system import SolarSystem
from app.models.user import User

from app.schemas.alert import AlertResponse

from app.security import (
    get_current_user,
    require_roles,
)

from app.services.audit import log_action
from app.services.alert_lifecycle import (
    acknowledge_alert_record,
    resolve_alert_record,
)


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
)


# ============================================================
# GET ALERTS
# ============================================================

@router.get(
    "/",
    response_model=list[AlertResponse]
)
def get_alerts(
    solar_system_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    query = db.query(Alert)

    # Customers can only see alerts belonging
    # to their own solar systems.
    if current_user.role == "customer":

        if current_user.customer_id is None:
            return []

        query = (
            query
            .join(
                SolarSystem,
                Alert.solar_system_id == SolarSystem.id
            )
            .filter(
                SolarSystem.customer_id
                == current_user.customer_id
            )
        )

    if solar_system_id is not None:
        query = query.filter(
            Alert.solar_system_id == solar_system_id
        )

    if status is not None:
        query = query.filter(
            Alert.status == status
        )

    return (
        query
        .order_by(Alert.created_at.desc())
        .all()
    )


# ============================================================
# GET ONE ALERT
# ============================================================

@router.get(
    "/{alert_id}",
    response_model=AlertResponse
)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    # Customer ownership protection
    if current_user.role == "customer":

        solar_system = (
            db.query(SolarSystem)
            .filter(
                SolarSystem.id == alert.solar_system_id
            )
            .first()
        )

        if (
            not solar_system
            or current_user.customer_id is None
            or solar_system.customer_id
            != current_user.customer_id
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to access this alert"
                )
            )

    return alert


# ============================================================
# ACKNOWLEDGE ALERT
# Admin / Technician
# ============================================================

@router.put(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse
)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "technician")
    ),
):

    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    try:
        acknowledge_alert_record(alert)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    log_action(
        db=db,
        user_id=current_user.id,
        action="ACKNOWLEDGE_ALERT",
        resource_type="alert",
        resource_id=alert.id,
        details=(
            f"Alert {alert.id} acknowledged "
            f"for solar system {alert.solar_system_id}."
        ),
    )

    db.commit()
    db.refresh(alert)

    return alert


# ============================================================
# RESOLVE ALERT
# Admin / Technician
# ============================================================

@router.put(
    "/{alert_id}/resolve",
    response_model=AlertResponse
)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "technician")
    ),
):

    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    try:
        resolve_alert_record(alert)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    log_action(
        db=db,
        user_id=current_user.id,
        action="RESOLVE_ALERT",
        resource_type="alert",
        resource_id=alert.id,
        details=(
            f"Alert {alert.id} resolved "
            f"for solar system {alert.solar_system_id}."
        ),
    )

    db.commit()
    db.refresh(alert)

    return alert

# ============================================================
# DELETE ALERT
# Admin Only
# ============================================================

@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    ),
):
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    solar_system_id = alert.solar_system_id

    # Record the deletion before removing the alert.
    log_action(
        db=db,
        user_id=current_user.id,
        action="DELETE_ALERT",
        resource_type="alert",
        resource_id=alert.id,
        details=(
            f"Alert {alert.id} permanently deleted "
            f"for solar system {solar_system_id}."
        ),
    )

    db.delete(alert)
    db.commit()

    return {
        "message": "Alert deleted successfully",
        "alert_id": alert_id
    }