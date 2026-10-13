
"""Phase 3A fault code API tests using isolated SQLite."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.security import get_current_user
from app.models.manufacturer_knowledge import (
    Manufacturer,
    EquipmentModel,
    TechnicalDocument,
)


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as db:
        manufacturer = Manufacturer(
            name="Test Fault Manufacturer",
            verification_status="pending",
        )
        db.add(manufacturer)
        db.flush()

        equipment = EquipmentModel(
            manufacturer_id=manufacturer.id,
            model_name="Test Inverter 5000",
            equipment_type="hybrid_inverter",
            technical_specs={},
            verification_status="pending",
        )
        other_equipment = EquipmentModel(
            manufacturer_id=manufacturer.id,
            model_name="Test Inverter 3000",
            equipment_type="hybrid_inverter",
            technical_specs={},
            verification_status="pending",
        )

        db.add_all([equipment, other_equipment])
        db.flush()

        document = TechnicalDocument(
            equipment_model_id=equipment.id,
            title="Test Troubleshooting Manual",
            document_type="troubleshooting_manual",
            source_url="https://example.com/manual.pdf",
            verification_status="pending",
        )
        db.add(document)
        db.flush()

        equipment_id = equipment.id
        other_equipment_id = other_equipment.id
        document_id = document.id

        db.commit()

    def override_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(
            id=1,
            role="admin",
            is_active=1,
        )
    )

    try:
        with TestClient(app) as test_client:
            yield (
                test_client,
                equipment_id,
                other_equipment_id,
                document_id,
            )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def fault_payload(equipment_id, document_id):
    return {
        "equipment_model_id": equipment_id,
        "source_document_id": document_id,
        "fault_code": "TEST-01",
        "description": "Simulated inverter fault for testing",
        "severity": "warning",
        "recommended_action": "Inspect the test equipment",
    }


def test_admin_creates_fault_code(client):
    api, equipment_id, _, document_id = client

    response = api.post(
        "/equipment-fault-codes",
        json=fault_payload(equipment_id, document_id),
    )

    assert response.status_code == 201, response.text
    assert response.json()["fault_code"] == "TEST-01"
    assert response.json()["verification_status"] == "pending"


def test_duplicate_fault_code_rejected(client):
    api, equipment_id, _, document_id = client

    payload = fault_payload(equipment_id, document_id)

    assert api.post(
        "/equipment-fault-codes", json=payload
    ).status_code == 201

    assert api.post(
        "/equipment-fault-codes", json=payload
    ).status_code == 409


def test_wrong_equipment_document_rejected(client):
    api, _, other_equipment_id, document_id = client

    response = api.post(
        "/equipment-fault-codes",
        json=fault_payload(other_equipment_id, document_id),
    )

    assert response.status_code == 422


def test_customer_cannot_create_fault_code(client):
    api, equipment_id, _, document_id = client

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(
            id=2,
            role="customer",
            is_active=1,
        )
    )

    response = api.post(
        "/equipment-fault-codes",
        json=fault_payload(equipment_id, document_id),
    )

    assert response.status_code == 403


def test_authenticated_user_can_list_fault_codes(client):
    api, equipment_id, _, document_id = client

    assert api.post(
        "/equipment-fault-codes",
        json=fault_payload(equipment_id, document_id),
    ).status_code == 201

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(
            id=2,
            role="customer",
            is_active=1,
        )
    )

    response = api.get(
        f"/equipment-fault-codes?equipment_model_id={equipment_id}"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_unknown_fault_code_returns_404(client):
    api, _, _, _ = client

    response = api.get("/equipment-fault-codes/999999")

    assert response.status_code == 404
