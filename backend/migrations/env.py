
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.config import DATABASE_URL
from app.database import Base

# Import all models so Alembic can discover their tables.
from app.models.customer import Customer
from app.models.solar_system import SolarSystem
from app.models.maintenance import MaintenanceRecord
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.telemetry import Telemetry
from app.models.alert import Alert
from app.models.device import Device
from app.models.device_request_nonce import DeviceRequestNonce
from app.models.manufacturer_pdf_review import ManufacturerPDFReview

from app.models.ai_conversation import (
    AIConversationSession,
    AIConversationMessage,
)

from app.models.manufacturer_knowledge import (
    Manufacturer,
    EquipmentModel,
    TechnicalDocument,
    EquipmentFaultCode,
)



# ============================================================
# ALEMBIC CONFIGURATION
# ============================================================

config = context.config

# Use the same database URL as the FastAPI application.
# Escape percent signs for ConfigParser interpolation.
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata containing all SQLAlchemy models.
target_metadata = Base.metadata


# ============================================================
# OFFLINE MIGRATION
# ============================================================

def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================
# ONLINE MIGRATION
# ============================================================

def run_migrations_online() -> None:
    """Run migrations using an active database connection."""

    engine_options = {
        "poolclass": pool.NullPool,
    }

    # Neon PostgreSQL connection configuration.
    # Disable native hstore detection to avoid the
    # connection initialization failure encountered earlier.
    if DATABASE_URL.startswith(("postgresql", "postgres://")):
        engine_options["use_native_hstore"] = False
        engine_options["connect_args"] = {
            "connect_timeout": 15,
        }

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {}
        ),
        prefix="sqlalchemy.",
        **engine_options,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


# ============================================================
# RUN ALEMBIC
# ============================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
