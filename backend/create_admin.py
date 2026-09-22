from app.database import (
    Base,
    engine,
    SessionLocal
)

# IMPORTANT:
# Import all models so SQLAlchemy knows every table
from app.models.customer import Customer
from app.models.solar_system import SolarSystem
from app.models.maintenance import MaintenanceRecord
from app.models.user import User

from app.security import hash_password


# ============================================================
# CREATE TABLES
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# DATABASE SESSION
# ============================================================

db = SessionLocal()


try:

    email = input(
        "Admin email: "
    ).strip().lower()

    full_name = input(
        "Admin full name: "
    ).strip()

    password = input(
        "Admin password: "
    )


    # ========================================================
    # PASSWORD VALIDATION
    # ========================================================

    if len(password) < 8:

        print(
            "Password must be at least 8 characters."
        )


    else:

        # ====================================================
        # CHECK EXISTING USER
        # ====================================================

        existing = (
            db.query(User)
            .filter(
                User.email == email
            )
            .first()
        )


        if existing:

            print(
                "A user with that email already exists."
            )


        else:

            # =================================================
            # CREATE ADMIN
            # =================================================

            admin = User(
                full_name=full_name,
                email=email,
                hashed_password=hash_password(
                    password
                ),
                role="admin",
                is_active=1
            )


            db.add(
                admin
            )

            db.commit()

            db.refresh(
                admin
            )


            print(
                "\nAdmin account created successfully!"
            )

            print(
                "Admin ID:",
                admin.id
            )

            print(
                "Email:",
                admin.email
            )

            print(
                "Role:",
                admin.role
            )


finally:

    db.close()