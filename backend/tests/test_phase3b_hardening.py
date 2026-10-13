"""Isolated Phase 3B security regression tests."""
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.manufacturer_knowledge import Manufacturer, EquipmentModel, TechnicalDocument, EquipmentFaultCode

@pytest.fixture
def env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        m = Manufacturer(name='Evidence Test Manufacturer'); db.add(m); db.flush()
        e = EquipmentModel(manufacturer_id=m.id, model_name='Evidence Test Inverter', equipment_type='inverter', technical_specs={}); db.add(e); db.flush()
        d = TechnicalDocument(equipment_model_id=e.id, title='Evidence Test Manual', document_type='manual', source_url='https://example.com/manual.pdf'); db.add(d); db.flush()
        f = EquipmentFaultCode(equipment_model_id=e.id, source_document_id=d.id, fault_code='TEST-01', description='Simulated test fault'); db.add(f); db.flush()
        ids = dict(manufacturer=m.id, equipment_model=e.id, technical_document=d.id, fault_code=f.id)
        db.commit()
    def override_db():
        with Session() as db: yield db
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='admin', is_active=True)
    try:
        with TestClient(app) as client: yield client, ids, Session
    finally:
        app.dependency_overrides.clear(); engine.dispose()

def verify(c, kind, id, evidence='https://example.com/manual.pdf'):
    return c.post(f'/manufacturer-knowledge/{kind}/{id}/verify', json={'verification_note': 'Manually reviewed test evidence', 'evidence_url': evidence})

def test_requires_evidence(env):
    c, ids, _ = env
    assert c.post(f'/manufacturer-knowledge/manufacturer/{ids["manufacturer"]}/verify', json={'verification_note': 'Reviewed by an administrator'}).status_code == 422

def test_invalid_evidence_rejected(env):
    c, ids, _ = env
    assert verify(c, 'manufacturer', ids['manufacturer'], 'http://example.com/manual.pdf').status_code == 422

def test_dependency_order(env):
    c, ids, _ = env
    assert verify(c, 'equipment_model', ids['equipment_model']).status_code == 422

def test_verified_chain_and_revoke(env):
    c, ids, Session = env
    assert c.get(f'/manufacturer-knowledge/trusted-fault-codes/{ids["equipment_model"]}').json() == []
    for kind in ('manufacturer', 'equipment_model', 'technical_document', 'fault_code'):
        r = verify(c, kind, ids[kind]); assert r.status_code == 200, r.text
    assert len(c.get(f'/manufacturer-knowledge/trusted-fault-codes/{ids["equipment_model"]}').json()) == 1
    r = c.post(f'/manufacturer-knowledge/technical_document/{ids["technical_document"]}/revoke', json={'reason': 'Manufacturer document has been withdrawn'})
    assert r.status_code == 200, r.text
    assert r.json()['records_revoked'] == 2
    assert c.get(f'/manufacturer-knowledge/trusted-fault-codes/{ids["equipment_model"]}').json() == []
    with Session() as db:
        assert db.query(AuditLog).filter(AuditLog.action == 'manufacturer_knowledge_revoked').count() == 2

def test_customer_cannot_approve_or_revoke(env):
    c, ids, _ = env
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role='customer', is_active=True)
    assert verify(c, 'manufacturer', ids['manufacturer']).status_code == 403
    assert c.post(f'/manufacturer-knowledge/manufacturer/{ids["manufacturer"]}/revoke', json={'reason': 'This record is not reliable'}).status_code == 403

def test_wrong_document_evidence_rejected(env):
    c, ids, _ = env
    for kind in ('manufacturer', 'equipment_model'):
        assert verify(c, kind, ids[kind]).status_code == 200
    assert verify(c, 'technical_document', ids['technical_document'], 'https://example.com/other.pdf').status_code == 422
