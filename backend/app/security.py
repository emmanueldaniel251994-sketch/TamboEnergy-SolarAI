import os

import jwt

from datetime import (
    datetime,
    timedelta,
    timezone
)

from dotenv import load_dotenv

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

from jwt.exceptions import InvalidTokenError

from pwdlib import PasswordHash

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User


load_dotenv()


SECRET_KEY = os.getenv(
    "SECRET_KEY"
)

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60"
    )
)


if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is missing from .env"
    )


password_hash = PasswordHash.recommended()

security = HTTPBearer()


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password: str):

    return password_hash.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str
):

    return password_hash.verify(
        plain_password,
        hashed_password
    )


# ============================================================
# JWT TOKEN
# ============================================================

def create_access_token(
    user_id: int,
    role: str
):

    expires = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token"
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get(
            "sub"
        )

        if user_id is None:
            raise unauthorized

    except InvalidTokenError:

        raise unauthorized


    user = (
        db.query(User)
        .filter(
            User.id == int(user_id)
        )
        .first()
    )

    if not user:
        raise unauthorized

    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="User account is disabled"
        )

    return user


# ============================================================
# ROLE PROTECTION
# ============================================================

def require_roles(*allowed_roles):

    def role_checker(
        current_user: User = Depends(
            get_current_user
        )
    ):

        if (
            current_user.role
            not in allowed_roles
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to perform this action"
                )
            )

        return current_user

    return role_checker