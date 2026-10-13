
"""Phase 3B manufacturer knowledge verification tests."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.security import get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.manufacturer_knowledge import (
    Manufacturer,
    EquipmentModel,
    TechnicalDocument,
    EquipmentFaultCode,
)


@pytest.fixture
def setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        admin = User(
            full_name="Verification Test Admin",
            email="verification-admin@example.com",
            hashed_password="test-hash",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.flush()

        manufacturer = Manufacturer(name="Verification Test Manufacturer")
        db.add(manufacturer)
        db.flush()

        equipment = EquipmentModel(
            manufacturer_id=manufacturer.id,
            model_name="Test Hybrid 5000",
            equipment_type="inverter",
            technical_specs={},
        )
        db.add(equipment)
        db.flush()

        document = TechnicalDocument(
            equipment_model_id=equipment.id,
            title="Test Manufacturer Manual",
            document_type="manual",
            source_url="https://example.com/test-manual.pdf",
        )
        db.add(document)
        db.flush()

        fault = EquipmentFaultCode(
            equipment_model_id=equipment.id,
            source_document_id=document.id,
            fault_code="TEST-01",
            description="Simulated fault for verification tests",
        )
        db.add(fault)
        db.flush()

        ids = {
            "admin": admin.id,
            "manufacturer": manufacturer.id,
            "equipment_model": equipment.id,
            "technical_document": document.id,
            "fault_code": fault.id,
        }
        db.commit()

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(
            id=ids["admin"],
            role="admin",
            is_active=True,
        )
    )

    try:
        with TestClient(app) as client:
            yield client, ids, SessionLocal
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def verify(client, resource_type, resource_id):
    return client.post(
        f"/manufacturer-knowledge/{resource_type}/{resource_id}/verify",
        json={
            "verification_note": (
                "Test evidence reviewed for automated verification"
            )
        },
    )


def test_manufacturer_verification(setup):
    client, ids, _ = setup

    response = verify(client, "manufacturer", ids["manufacturer"])

    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "verified"


def test_equipment_requires_verified_manufacturer(setup):
    client, ids, _ = setup

    response = verify(client, "equipment_model", ids["equipment_model"])

    assert response.status_code == 422


def test_document_requires_verified_equipment(setup):
    client, ids, _ = setup

    response = verify(
        client, "technical_document", ids["technical_document"]
    )

    assert response.status_code == 422


def test_fault_requires_verified_source(setup):
    client, ids, _ = setup

    response = verify(client, "fault_code", ids["fault_code"])

    assert response.status_code == 422


def test_full_verification_sequence(setup):
    client, ids, SessionLocal = setup

    for resource_type in (
        "manufacturer",
        "equipment_model",
        "technical_document",
        "fault_code",
    ):
        response = verify(client, resource_type, ids[resource_type])
        assert response.status_code == 200, response.text

    with SessionLocal() as db:
        audits = db.query(AuditLog).filter(
            AuditLog.action == "manufacturer_knowledge_verified"
        ).all()

        assert len(audits) == 4
        assert all(a.user_id == ids["admin"] for a in audits)


def test_duplicate_verification_rejected(setup):
    client, ids, _ = setup

    assert verify(
        client, "manufacturer", ids["manufacturer"]
    ).status_code == 200

    response = verify(client, "manufacturer", ids["manufacturer"])

    assert response.status_code == 409


def test_customer_cannot_verify(setup):
    client, ids, _ = setup

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(
            id=ids["admin"],
            role="customer",
            is_active=True,
        )
    )

    response = verify(client, "manufacturer", ids["manufacturer"])

    assert response.status_code == 403


def test_short_verification_note_rejected(setup):
    client, ids, _ = setup

    response = client.post(
        f"/manufacturer-knowledge/manufacturer/{ids['manufacturer']}/verify",
        json={"verification_note": "short"},
    )

    assert response.status_code == 422
