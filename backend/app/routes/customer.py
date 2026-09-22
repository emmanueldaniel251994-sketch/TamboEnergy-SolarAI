from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.customer import Customer
from app.models.user import User

from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse
)

from app.security import (
    get_current_user,
    require_roles
)

from app.services.audit import log_action


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


# ============================================================
# CREATE CUSTOMER
# ADMIN ONLY
# ============================================================

@router.post(
    "/",
    response_model=CustomerResponse
)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    new_customer = Customer(
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        address=customer.address
    )

    db.add(new_customer)

    # Generate ID before commit
    db.flush()

    log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="customer",
        resource_id=new_customer.id,
        details=(
            f"Created customer "
            f"{new_customer.name}"
        )
    )

    db.commit()
    db.refresh(new_customer)

    return new_customer


# ============================================================
# GET ALL CUSTOMERS
# ADMIN + TECHNICIAN
# ============================================================

@router.get(
    "/",
    response_model=list[CustomerResponse]
)
def get_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "admin",
            "technician"
        )
    )
):

    return db.query(
        Customer
    ).all()


# ============================================================
# CUSTOMER VIEW OWN PROFILE
# ============================================================

@router.get(
    "/my-profile",
    response_model=CustomerResponse
)
def get_my_customer_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):

    if not current_user.customer_id:

        raise HTTPException(
            status_code=404,
            detail=(
                "This user account is not "
                "linked to a customer profile"
            )
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id
            == current_user.customer_id
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )

    return customer


# ============================================================
# GET ONE CUSTOMER
# ADMIN + TECHNICIAN
# ============================================================

@router.get(
    "/{customer_id}",
    response_model=CustomerResponse
)
def get_customer(
    customer_id: int,
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
            Customer.id == customer_id
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer


# ============================================================
# UPDATE CUSTOMER
# ADMIN ONLY
# ============================================================

@router.put(
    "/{customer_id}",
    response_model=CustomerResponse
)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    update_data = (
        customer_update.model_dump(
            exclude_unset=True
        )
    )

    for field, value in update_data.items():

        setattr(
            customer,
            field,
            value
        )

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="customer",
        resource_id=customer.id,
        details=(
            f"Updated customer "
            f"{customer.name}"
        )
    )

    db.commit()
    db.refresh(customer)

    return customer


# ============================================================
# DELETE CUSTOMER
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{customer_id}"
)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id
        )
        .first()
    )

    if not customer:

        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    customer_name = customer.name
    saved_customer_id = customer.id

    db.delete(customer)

    log_action(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="customer",
        resource_id=saved_customer_id,
        details=(
            f"Deleted customer "
            f"{customer_name}"
        )
    )

    db.commit()

    return {
        "message":
            "Customer deleted successfully"
    }