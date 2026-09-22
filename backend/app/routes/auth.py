from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.user import User

from app.schemas.user import (
    UserRegister,
    UserLogin,
    AdminUserCreate,
    UserResponse,
    TokenResponse
)

from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_roles
)

from app.models.customer import Customer

from app.schemas.user import (
    UserRegister,
    UserLogin,
    AdminUserCreate,
    UserCustomerLink,
    UserRoleUpdate,
    UserResponse,
    TokenResponse
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ============================================================
# PUBLIC CUSTOMER REGISTRATION
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    email = (
        user_data.email
        .strip()
        .lower()
    )


    existing_user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )


    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    if len(user_data.password) < 8:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain "
                "at least 8 characters"
            )
        )


    new_user = User(
        full_name=user_data.full_name,
        email=email,
        hashed_password=hash_password(
            user_data.password
        ),

        # Public users cannot make
        # themselves administrators.
        role="customer"
    )


    db.add(
        new_user
    )

    db.commit()

    db.refresh(
        new_user
    )


    return new_user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):

    email = (
        credentials.email
        .strip()
        .lower()
    )


    user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )


    if not verify_password(
        credentials.password,
        user.hashed_password
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )


    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )


    token = create_access_token(
        user.id,
        user.role
    )


    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ============================================================
# CURRENT USER PROFILE
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse
)
def my_profile(
    current_user: User = Depends(
        get_current_user
    )
):

    return current_user


# ============================================================
# ADMIN: CREATE USER
# ============================================================

@router.post(
    "/users",
    response_model=UserResponse
)
def create_user_by_admin(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    valid_roles = {
        "admin",
        "technician",
        "customer"
    }


    if (
        user_data.role
        not in valid_roles
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )


    email = (
        user_data.email
        .strip()
        .lower()
    )


    existing_user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )


    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    if len(user_data.password) < 8:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain "
                "at least 8 characters"
            )
        )


    new_user = User(
        full_name=user_data.full_name,
        email=email,
        hashed_password=hash_password(
            user_data.password
        ),
        role=user_data.role,
        customer_id=user_data.customer_id
    )


    db.add(
        new_user
    )

    db.commit()

    db.refresh(
        new_user
    )


    return new_user


# ============================================================
# ADMIN: LIST USERS
# ============================================================

@router.get(
    "/users",
    response_model=list[UserResponse]
)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    return db.query(
        User
    ).all()

# ============================================================
# ADMIN: LINK USER TO CUSTOMER
# ============================================================

@router.put(
    "/users/{user_id}/customer",
    response_model=UserResponse
)
def link_user_to_customer(
    user_id: int,
    link_data: UserCustomerLink,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == link_data.customer_id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    user.customer_id = customer.id

    db.commit()
    db.refresh(user)

    return user


# ============================================================
# ADMIN: REMOVE CUSTOMER LINK
# ============================================================

@router.delete(
    "/users/{user_id}/customer",
    response_model=UserResponse
)
def unlink_user_from_customer(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.customer_id = None

    db.commit()
    db.refresh(user)

    return user


# ============================================================
# ADMIN: CHANGE USER ROLE
# ============================================================

@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse
)
def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    valid_roles = {
        "admin",
        "technician",
        "customer"
    }

    if role_data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.role = role_data.role

    db.commit()
    db.refresh(user)

    return user


# ============================================================
# ADMIN: ENABLE / DISABLE USER
# ============================================================

@router.put(
    "/users/{user_id}/status",
    response_model=UserResponse
)
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin")
    )
):

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot disable your own account"
        )

    user.is_active = (
        0 if user.is_active else 1
    )

    db.commit()
    db.refresh(user)

    return user