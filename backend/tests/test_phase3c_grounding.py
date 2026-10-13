"""Isolated regression tests: only fully verified evidence may be grounded."""
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.security import get_current_user
from app.models.manufacturer_knowledge import (
    Manufacturer, EquipmentModel, TechnicalDocument, EquipmentFaultCode,
)
from app.services.manufacturer_grounding import grounded_diagnostic


@pytest.fixture
def environment():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        m = Manufacturer(name="Fictional Test Manufacturer", verification_status="verified")
        db.add(m)
        db.flush()
        model = EquipmentModel(manufacturer_id=m.id, model_name="Fictional Model", equipment_type="inverter", technical_specs={}, verification_status="verified")
        db.add(model)
        db.flush()
        doc = TechnicalDocument(equipment_model_id=model.id, title="Synthetic Test Manual", document_type="manual", source_url="https://example.com/synthetic.pdf", verification_status="verified")
        db.add(doc)
        db.flush()
        fault = EquipmentFaultCode(equipment_model_id=model.id, source_document_id=doc.id, fault_code="TEST-01", description="Synthetic test-only description", severity="warning", verification_status="verified")
        db.add(fault)
        db.flush()
        ids = (m.id, model.id, doc.id, fault.id)
        db.commit()

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="technician", is_active=True)
    try:
        with TestClient(app) as client:
            yield client, SessionLocal, ids
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def call(client, model_id, code="TEST-01"):
    return client.post("/ai-assistant/manufacturer-diagnostic", json={"equipment_model_id": model_id, "fault_code": code})


def test_verified_exact_match_has_source(environment):
    client, _, ids = environment
    response = call(client, ids[1])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["grounded"] is True
    assert data["sources"][0]["source_url"] == "https://example.com/synthetic.pdf"


def test_unknown_code_fails_closed(environment):
    client, _, ids = environment
    data = call(client, ids[1], "NOT-THERE").json()
    assert data["grounded"] is False and data["sources"] == [] and data["matches"] == []


def test_pending_fault_excluded(environment):
    client, SessionLocal, ids = environment
    with SessionLocal() as db:
        db.get(EquipmentFaultCode, ids[3]).verification_status = "pending"
        db.commit()
    assert call(client, ids[1]).json()["grounded"] is False


def test_revoked_document_excluded(environment):
    client, SessionLocal, ids = environment
    with SessionLocal() as db:
        db.get(TechnicalDocument, ids[2]).verification_status = "revoked"
        db.commit()
    assert call(client, ids[1]).json()["grounded"] is False


def test_revoked_manufacturer_excluded(environment):
    client, SessionLocal, ids = environment
    with SessionLocal() as db:
        db.get(Manufacturer, ids[0]).verification_status = "revoked"
        db.commit()
    assert call(client, ids[1]).json()["grounded"] is False


def test_missing_model_404(environment):
    client, _, _ = environment
    assert call(client, 999999).status_code == 404


def test_blank_code_rejected(environment):
    client, _, ids = environment
    assert call(client, ids[1], "   ").status_code == 422


def test_customer_can_read_verified_knowledge(environment):
    client, _, ids = environment
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role="customer", is_active=True)
    assert call(client, ids[1]).status_code == 200
