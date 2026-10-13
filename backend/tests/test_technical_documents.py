
"""Phase 3A technical document API tests using isolated SQLite."""

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
            name="Test Document Manufacturer",
            verification_status="pending",
        )
        db.add(manufacturer)
        db.flush()

        equipment = EquipmentModel(
            manufacturer_id=manufacturer.id,
            model_name="Test Hybrid Inverter",
            equipment_type="hybrid_inverter",
            technical_specs={},
            verification_status="pending",
        )
        db.add(equipment)
        db.commit()
        equipment_id = equipment.id

    def override_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1, role="admin", is_active=1)
    )

    try:
        with TestClient(app) as test_client:
            yield test_client, equipment_id
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def document_payload(equipment_id):
    return {
        "equipment_model_id": equipment_id,
        "title": "Test Installation Manual",
        "document_type": "installation_manual",
        "source_url": "https://example.com/manual.pdf",
        "document_version": "1.0",
    }


def test_admin_creates_document(client):
    api, equipment_id = client

    response = api.post(
        "/technical-documents",
        json=document_payload(equipment_id),
    )

    assert response.status_code == 201, response.text
    assert response.json()["verification_status"] == "pending"
    assert response.json()["last_verified"] is None


def test_unknown_equipment_model_rejected(client):
    api, _ = client

    response = api.post(
        "/technical-documents",
        json=document_payload(999999),
    )

    assert response.status_code == 404


def test_invalid_document_url_rejected(client):
    api, equipment_id = client

    payload = document_payload(equipment_id)
    payload["source_url"] = "file:///etc/passwd"

    response = api.post("/technical-documents", json=payload)

    assert response.status_code == 422


def test_customer_cannot_register_document(client):
    api, equipment_id = client

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=2, role="customer", is_active=1)
    )

    response = api.post(
        "/technical-documents",
        json=document_payload(equipment_id),
    )

    assert response.status_code == 403


def test_authenticated_user_can_list_documents(client):
    api, equipment_id = client

    response = api.post(
        "/technical-documents",
        json=document_payload(equipment_id),
    )
    assert response.status_code == 201

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=2, role="customer", is_active=1)
    )

    response = api.get(
        f"/technical-documents?equipment_model_id={equipment_id}"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_unknown_document_returns_404(client):
    api, _ = client

    response = api.get("/technical-documents/999999")

    assert response.status_code == 404
