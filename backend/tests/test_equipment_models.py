
"""Phase 3A equipment model API tests using isolated SQLite."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.security import get_current_user
from app.models.manufacturer_knowledge import Manufacturer


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)

    db = TestingSession()
    manufacturer = Manufacturer(
        name="Test Manufacturer",
        verification_status="pending",
    )
    db.add(manufacturer)
    db.commit()
    manufacturer_id = manufacturer.id
    db.close()

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1, role="admin", is_active=1)
    )

    try:
        with TestClient(app) as test_client:
            yield test_client, manufacturer_id
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_creates_equipment_model(client):
    api, manufacturer_id = client

    response = api.post(
        "/equipment-models",
        json={
            "manufacturer_id": manufacturer_id,
            "model_name": "Test Hybrid 5000",
            "equipment_type": "hybrid_inverter",
            "technical_specs": {"rated_power_w": 5000},
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["model_name"] == "Test Hybrid 5000"
    assert response.json()["verification_status"] == "pending"


def test_duplicate_equipment_model_rejected(client):
    api, manufacturer_id = client

    payload = {
        "manufacturer_id": manufacturer_id,
        "model_name": "Test Hybrid 5000",
        "equipment_type": "hybrid_inverter",
    }

    assert api.post("/equipment-models", json=payload).status_code == 201
    assert api.post("/equipment-models", json=payload).status_code == 409


def test_unknown_manufacturer_rejected(client):
    api, _ = client

    response = api.post(
        "/equipment-models",
        json={
            "manufacturer_id": 999999,
            "model_name": "Unknown Model",
            "equipment_type": "inverter",
        },
    )

    assert response.status_code == 404


def test_customer_cannot_register_model(client):
    api, manufacturer_id = client

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=2, role="customer", is_active=1)
    )

    response = api.post(
        "/equipment-models",
        json={
            "manufacturer_id": manufacturer_id,
            "model_name": "Unauthorized Model",
            "equipment_type": "inverter",
        },
    )

    assert response.status_code == 403


def test_authenticated_user_can_list_models(client):
    api, _ = client

    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=2, role="customer", is_active=1)
    )

    response = api.get("/equipment-models")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unknown_equipment_model_returns_404(client):
    api, _ = client

    response = api.get("/equipment-models/999999")

    assert response.status_code == 404
