import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-solarai-tests")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.device_security import (
    generate_device_api_key,
    hash_device_api_key,
    verify_device_api_key,
)
from app.models.alert import Alert
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.customer import Customer
from app.models.device import Device  # noqa: F401
from app.models.maintenance import MaintenanceRecord  # noqa: F401
from app.models.solar_system import SolarSystem
from app.models.telemetry import Telemetry  # noqa: F401
from app.models.user import User
from app.services.alert_lifecycle import (
    acknowledge_alert_record,
    resolve_alert_record,
)
from app.schemas.telemetry import TelemetryCreate
from app.services import telemetry_processor


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def full_telemetry(**overrides):
    values = {
        "solar_system_id": 1,
        "pv_voltage": 125.0,
        "pv_current": 9.5,
        "pv_power": 1187.5,
        "battery_voltage": 51.4,
        "battery_current": 7.5,
        "battery_soc": 80.0,
        "load_power": 650.0,
        "temperature": 31.0,
        "error_code": None,
    }
    values.update(overrides)
    return TelemetryCreate(**values)


def disable_alert_creation(monkeypatch):
    monkeypatch.setattr(
        telemetry_processor,
        "create_fault_alert",
        lambda db, telemetry: None,
    )


def test_device_api_key_is_hashed_and_verifiable():
    raw_key = generate_device_api_key()
    stored_hash = hash_device_api_key(raw_key)

    assert raw_key.startswith("tambo_dev_")
    assert raw_key != stored_hash
    assert verify_device_api_key(raw_key, stored_hash) is True
    assert verify_device_api_key("tambo_dev_wrong", stored_hash) is False


def test_incomplete_telemetry_disables_ml(db_session, monkeypatch):
    disable_alert_creation(monkeypatch)

    telemetry = TelemetryCreate(
        solar_system_id=1,
        pv_voltage=125.0,
        battery_voltage=51.4,
        battery_soc=80.0,
        temperature=31.0,
    )

    record = telemetry_processor.process_telemetry(db_session, telemetry)

    assert record.data_quality_score == 50.0
    assert record.ml_prediction_available == 0
    assert record.prediction_agreement == "not_available"
    assert record.needs_review == 1


def test_safety_rule_wins_disagreement(db_session, monkeypatch):
    disable_alert_creation(monkeypatch)
    monkeypatch.setattr(
        telemetry_processor,
        "predict_fault",
        lambda **kwargs: {
            "predicted_fault": "normal",
            "confidence": 0.99,
            "prediction_available": True,
        },
    )

    record = telemetry_processor.process_telemetry(
        db_session,
        full_telemetry(battery_voltage=45.9),
    )

    assert record.fault_type == "battery_undervoltage"
    assert record.prediction_agreement == "disagree"
    assert record.final_diagnosis == "battery_undervoltage"
    assert record.needs_review == 1


def test_high_confidence_non_safety_ml_can_override(db_session, monkeypatch):
    disable_alert_creation(monkeypatch)
    monkeypatch.setattr(
        telemetry_processor,
        "predict_fault",
        lambda **kwargs: {
            "predicted_fault": "high_load",
            "confidence": 0.96,
            "prediction_available": True,
        },
    )

    record = telemetry_processor.process_telemetry(
        db_session,
        full_telemetry(load_power=2800.0),
    )

    assert record.fault_type == "normal"
    assert record.prediction_agreement == "disagree"
    assert record.final_diagnosis == "high_load"
    assert record.needs_review == 1


def test_device_provenance_is_stored(db_session, monkeypatch):
    disable_alert_creation(monkeypatch)
    monkeypatch.setattr(
        telemetry_processor,
        "predict_fault",
        lambda **kwargs: {
            "predicted_fault": "normal",
            "confidence": 0.95,
            "prediction_available": True,
        },
    )

    customer = Customer(name="Test Customer")
    db_session.add(customer)
    db_session.flush()

    system = SolarSystem(customer_id=customer.id, location="Test Site")
    db_session.add(system)
    db_session.flush()

    device = Device(
        solar_system_id=system.id,
        device_name="Test Gateway",
        device_type="monitoring_gateway",
        api_key_hash="a" * 64,
        is_active=True,
    )
    db_session.add(device)
    db_session.flush()

    record = telemetry_processor.process_telemetry(
        db_session,
        full_telemetry(solar_system_id=system.id),
        device_id=device.id,
    )
    db_session.flush()

    stored = db_session.query(Telemetry).filter(Telemetry.id == record.id).one()
    assert stored.device_id == device.id


def test_alert_lifecycle_requires_acknowledgement():
    class ExampleAlert:
        status = "open"
        acknowledged_at = None
        resolved_at = None

    alert = ExampleAlert()

    with pytest.raises(ValueError):
        resolve_alert_record(alert)

    acknowledge_alert_record(alert)
    assert alert.status == "acknowledged"
    assert alert.acknowledged_at is not None

    resolve_alert_record(alert)
    assert alert.status == "resolved"
    assert alert.resolved_at is not None
