from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.maintenance import (
    MaintenanceRecord
)

from app.models.solar_system import (
    SolarSystem
)

from app.models.user import User

from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceUpdate,
    MaintenanceResponse
)

from app.security import (
    get_current_user,
    require_roles
)

from app.services.audit import log_action


router = APIRouter(
    prefix="/maintenance",
    tags=["Maintenance"]
)


# ============================================================
# CREATE
# ADMIN + TECHNICIAN
# ============================================================

@router.post(
    "/",
    response_model=MaintenanceResponse
)
def create_maintenance_record(
    record: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "admin",
            "technician"
        )
    )
):

    system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id
            == record.solar_system_id
        )
        .first()
    )

    if not system:

        raise HTTPException(
            status_code=404,
            detail="Solar system not found"
        )

    new_record = MaintenanceRecord(
        solar_system_id=(
            record.solar_system_id
        ),
        issue=record.issue,
        action_taken=(
            record.action_taken
        ),
        status=record.status,
        technician=record.technician
    )

    db.add(new_record)
    db.flush()

    log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="maintenance",
        resource_id=new_record.id,
        details=(
            "Created maintenance record "
            f"for solar system "
            f"{new_record.solar_system_id}"
        )
    )

    db.commit()
    db.refresh(new_record)

    return new_record


# ============================================================
# GET ALL / OWN
# ============================================================

@router.get(
    "/",
    response_model=list[
        MaintenanceResponse
    ]
)
def get_maintenance_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    if current_user.role in {
        "admin",
        "technician"
    }:

        return db.query(
            MaintenanceRecord
        ).all()

    if current_user.role == "customer":

        if not current_user.customer_id:

            return []

        return (
            db.query(MaintenanceRecord)
            .join(
                SolarSystem,
                MaintenanceRecord.solar_system_id
                == SolarSystem.id
            )
            .filter(
                SolarSystem.customer_id
                == current_user.customer_id
            )
            .all()
        )

    raise HTTPException(
        status_code=403,
        detail="Access denied"
    )


# ============================================================
# GET ONE
# ============================================================

@router.get(
    "/{record_id}",
    response_model=MaintenanceResponse
)
def get_maintenance_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    record = (
        db.query(MaintenanceRecord)
        .filter(
            MaintenanceRecord.id
            == record_id
        )
        .first()
    )

    if not record:

        raise HTTPException(
            status_code=404,
            detail=(
                "Maintenance record "
                "not found"
            )
        )

    if current_user.role == "customer":

        system = (
            db.query(SolarSystem)
            .filter(
                SolarSystem.id
                == record.solar_system_id
            )
            .first()
        )

        if (
            not system
            or system.customer_id
            != current_user.customer_id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to view this record"
                )
            )

    return record


# ============================================================
# UPDATE
# ADMIN + TECHNICIAN
# ============================================================

@router.put(
    "/{record_id}",
    response_model=MaintenanceResponse
)
def update_maintenance_record(
    record_id: int,
    record_update: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "admin",
            "technician"
        )
    )
):

    record = (
        db.query(MaintenanceRecord)
        .filter(
            MaintenanceRecord.id
            == record_id
        )
        .first()
    )

    if not record:

        raise HTTPException(
            status_code=404,
            detail=(
                "Maintenance record "
                "not found"
            )
        )

    update_data = (
        record_update.model_dump(
            exclude_unset=True
        )
    )

    for field, value in update_data.items():

        setattr(
            record,
            field,
            value
        )

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="maintenance",
        resource_id=record.id,
        details=(
            "Updated maintenance record "
            f"{record.id}"
        )
    )

    db.commit()
    db.refresh(record)

    return record


# ============================================================
# DELETE
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{record_id}"
)
def delete_maintenance_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    record = (
        db.query(MaintenanceRecord)
        .filter(
            MaintenanceRecord.id
            == record_id
        )
        .first()
    )

    if not record:

        raise HTTPException(
            status_code=404,
            detail=(
                "Maintenance record "
                "not found"
            )
        )

    saved_record_id = record.id

    db.delete(record)

    log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="maintenance",
        resource_id=saved_record_id,
        details=(
            "Deleted maintenance record "
            f"{saved_record_id}"
        )
    )

    db.commit()

    return {
        "message": (
            "Maintenance record "
            "deleted successfully"
        )
    }