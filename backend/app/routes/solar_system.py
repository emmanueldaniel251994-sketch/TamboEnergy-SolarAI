from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.customer import Customer
from app.models.solar_system import SolarSystem
from app.models.user import User

from app.schemas.solar_system import (
    SolarSystemCreate,
    SolarSystemUpdate,
    SolarSystemResponse
)

from app.security import (
    get_current_user,
    require_roles
)

from app.services.audit import log_action


router = APIRouter(
    prefix="/solar-systems",
    tags=["Solar Systems"]
)


# ============================================================
# CREATE
# ADMIN + TECHNICIAN
# ============================================================

@router.post(
    "/",
    response_model=SolarSystemResponse
)
def create_solar_system(
    system: SolarSystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "admin",
            "technician"
        )
    )
):

    customer = (
        db.query(Customer)
        .filter(
            Customer.id
            == system.customer_id
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    new_system = SolarSystem(
        customer_id=system.customer_id,
        inverter_brand=(
            system.inverter_brand
        ),
        inverter_capacity_kva=(
            system.inverter_capacity_kva
        ),
        battery_type=(
            system.battery_type
        ),
        battery_capacity_kwh=(
            system.battery_capacity_kwh
        ),
        panel_count=(
            system.panel_count
        ),
        panel_wattage=(
            system.panel_wattage
        ),
        location=system.location
    )

    db.add(new_system)
    db.flush()

    log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="solar_system",
        resource_id=new_system.id,
        details=(
            "Created solar system for "
            f"customer {new_system.customer_id}"
        )
    )

    db.commit()
    db.refresh(new_system)

    return new_system


# ============================================================
# GET ALL / OWN SYSTEMS
# ============================================================

@router.get(
    "/",
    response_model=list[
        SolarSystemResponse
    ]
)
def get_solar_systems(
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
            SolarSystem
        ).all()

    if current_user.role == "customer":

        if not current_user.customer_id:

            return []

        return (
            db.query(SolarSystem)
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
    "/{system_id}",
    response_model=SolarSystemResponse
)
def get_solar_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id == system_id
        )
        .first()
    )

    if not system:

        raise HTTPException(
            status_code=404,
            detail="Solar system not found"
        )

    if current_user.role == "customer":

        if (
            system.customer_id
            != current_user.customer_id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to view this solar system"
                )
            )

    return system


# ============================================================
# UPDATE
# ADMIN + TECHNICIAN
# ============================================================

@router.put(
    "/{system_id}",
    response_model=SolarSystemResponse
)
def update_solar_system(
    system_id: int,
    system_update: SolarSystemUpdate,
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
            SolarSystem.id == system_id
        )
        .first()
    )

    if not system:

        raise HTTPException(
            status_code=404,
            detail="Solar system not found"
        )

    update_data = (
        system_update.model_dump(
            exclude_unset=True
        )
    )

    for field, value in update_data.items():

        setattr(
            system,
            field,
            value
        )

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="solar_system",
        resource_id=system.id,
        details=(
            f"Updated solar system "
            f"{system.id}"
        )
    )

    db.commit()
    db.refresh(system)

    return system


# ============================================================
# DELETE
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{system_id}"
)
def delete_solar_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id == system_id
        )
        .first()
    )

    if not system:

        raise HTTPException(
            status_code=404,
            detail="Solar system not found"
        )

    saved_system_id = system.id

    db.delete(system)

    log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="solar_system",
        resource_id=saved_system_id,
        details=(
            f"Deleted solar system "
            f"{saved_system_id}"
        )
    )

    db.commit()

    return {
        "message":
            "Solar system deleted successfully"
    }