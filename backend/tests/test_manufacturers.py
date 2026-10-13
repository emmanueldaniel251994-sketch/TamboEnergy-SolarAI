
"""Phase 3A manufacturer API tests using isolated SQLite."""

import pytest
from types import SimpleNamespace

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

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=1, role="admin", is_active=1)
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_creates_manufacturer(client):
    response = client.post(
        "/manufacturers",
        json={"name": "Test Solar Manufacturer"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["verification_status"] == "pending"


def test_duplicate_manufacturer_rejected(client):
    payload = {"name": "Test Solar Manufacturer"}
    assert client.post("/manufacturers", json=payload).status_code == 201
    response = client.post("/manufacturers", json=payload)
    assert response.status_code == 409


def test_customer_cannot_create_manufacturer(client):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=2, role="customer", is_active=1)
    )
    response = client.post(
        "/manufacturers",
        json={"name": "Unauthorized Manufacturer"},
    )
    assert response.status_code == 403


def test_authenticated_user_can_list_manufacturers(client):
    app.dependency_overrides[get_current_user] = (
        lambda: SimpleNamespace(id=2, role="customer", is_active=1)
    )
    response = client.get("/manufacturers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unknown_manufacturer_returns_404(client):
    response = client.get("/manufacturers/999999")
    assert response.status_code == 404
