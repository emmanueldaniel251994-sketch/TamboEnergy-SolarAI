"""Manufacturer evidence is exact-model, revocation-aware, and safety-gated."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.ai_conversation import AIConversationMessage
from app.models.manufacturer_knowledge import Manufacturer, EquipmentModel, TechnicalDocument, EquipmentFaultCode
from app.security import get_current_user


@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(conn, record):
        conn.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        db.add_all([User(id=1,full_name='Customer',email='customer@test.example',hashed_password='synthetic',role='customer',is_active=1),
                    User(id=2,full_name='Admin',email='admin@test.example',hashed_password='synthetic',role='admin',is_active=1)])
        maker = Manufacturer(name='Brand A',verification_status='verified')
        db.add(maker); db.flush()
        model = EquipmentModel(manufacturer_id=maker.id,model_name='Model A',equipment_type='hybrid_inverter',technical_specs={},verification_status='verified')
        db.add(model); db.flush()
        document = TechnicalDocument(equipment_model_id=model.id,title='Official manual',document_type='manual',source_url='https://manufacturer.example/manual',verification_status='verified',document_version='1')
        db.add(document); db.flush()
        fault = EquipmentFaultCode(equipment_model_id=model.id,source_document_id=document.id,fault_code='F01',description='Communication alarm.',severity='warning',recommended_action='documented-action-not-to-inject',verification_status='verified')
        db.add(fault); db.commit()
        ids = (maker.id,model.id,document.id,fault.id)
    def database():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1,role='customer',is_active=1)
    try:
        with TestClient(app) as api:
            yield api, sessions, ids
    finally:
        app.dependency_overrides.clear(); engine.dispose()


def start(setup, question='What does fault code F01 mean?', **profile):
    api, _, ids = setup
    body = {'equipment_model_id':ids[1], 'fault_code':'F01', **profile}
    response = api.post('/ai-assistant/sessions',json={'question':question,'profile':body})
    assert response.status_code == 201, response.text
    return response.json()


def test_verified_exact_model_evidence_has_sources_without_action_injection(setup):
    result = start(setup)['response']['manufacturer_evidence']
    assert result['grounded']
    assert result['matches'][0]['description'] == 'Communication alarm.'
    assert result['sources'][0]['title'] == 'Official manual'
    assert 'documented-action-not-to-inject' not in str(result)


@pytest.mark.parametrize('resource_index,kind', [(0,Manufacturer),(1,EquipmentModel),(2,TechnicalDocument),(3,EquipmentFaultCode)])
def test_unverified_dependency_fails_closed(setup, resource_index, kind):
    _, sessions, ids = setup
    with sessions() as db:
        db.get(kind, ids[resource_index]).verification_status = 'pending'; db.commit()
    result = start(setup)['response']['manufacturer_evidence']
    assert not result['grounded']
    assert result['matches'] == result['sources'] == []


def test_exact_code_required_without_padding_or_alias_guess(setup):
    result = start(setup, fault_code='01')['response']['manufacturer_evidence']
    assert result['status'] == 'no_verified_match'


def test_reported_model_mismatch_withholds_wrong_equipment_evidence(setup):
    result = start(setup, inverter_model='Different model')['response']['manufacturer_evidence']
    assert result['status'] == 'model_mismatch'
    assert result['sources'] == []


@pytest.mark.parametrize('question,profile', [
    ('Battery is smoking and sparking', {}),
    ('What does fault code F01 mean?', {'system_type':'industrial','rated_capacity_kva':500}),
])
def test_emergency_and_industrial_escalation_take_priority(setup, question, profile):
    result = start(setup,question,**profile)['response']['manufacturer_evidence']
    assert result['status'] == 'withheld'
    assert result['sources'] == result['matches'] == []


def test_hazardous_verified_registry_content_is_not_exposed(setup):
    _, sessions, ids = setup
    with sessions() as db:
        db.get(EquipmentFaultCode,ids[3]).recommended_action = 'disable bms and bypass protection'; db.commit()
    result = start(setup)['response']['manufacturer_evidence']
    assert result['status'] == 'withheld'
    assert 'disable bms' not in str(result)


def test_revocation_is_rechecked_on_reopen_without_rewriting_snapshot(setup):
    api, sessions, ids = setup
    sid = start(setup)['session_id']
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2,role='admin',is_active=1)
    revoke = api.post(f'/manufacturer-knowledge/technical_document/{ids[2]}/revoke',json={'reason':'The independent evidence was withdrawn.'})
    assert revoke.status_code == 200, revoke.text
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1,role='customer',is_active=1)
    detail = api.get(f'/ai-assistant/sessions/{sid}').json()
    result = detail['messages'][1]['response_metadata']['manufacturer_evidence']
    assert not result['grounded']
    assert result['sources'] == []
    with sessions() as db:
        stored = db.query(AIConversationMessage).filter_by(session_id=sid,role='assistant').one()
        assert stored.response_metadata['manufacturer_evidence']['grounded']


def test_followup_preserves_selected_model_and_can_clear_it(setup):
    api, _, ids = setup
    sid = start(setup)['session_id']
    follow = api.post(f'/ai-assistant/sessions/{sid}/messages',json={'question':'SOC is 45%'})
    assert follow.status_code == 200, follow.text
    assert follow.json()['response']['profile']['equipment_model_id'] == ids[1]
    assert follow.json()['response']['manufacturer_evidence']['grounded']
    clear = api.post(f'/ai-assistant/sessions/{sid}/messages',json={'question':'Continue general guidance','updates':{'equipment_model_id':None}})
    assert clear.status_code == 200, clear.text
    assert clear.json()['response']['manufacturer_evidence'] is None


def test_rejected_quality_review_cannot_be_overridden_by_verified_registry(setup):
    from app.diagnostics.quality_gate import QualityReview
    from app.diagnostics.engine import diagnose, DiagnosticRequest
    baseline = diagnose(DiagnosticRequest(question='What does fault code F01 mean?'))
    baseline.status = 'manual_review_required'
    with patch('app.diagnostics.conversation.diagnose_checked', return_value=QualityReview(passed=False,disposition='withheld',result=baseline)):
        response = start(setup)['response']
    assert not response['quality_review_passed']
    assert response['manufacturer_evidence']['status'] == 'withheld'


def test_history_reuses_lookup_when_only_measurements_change(setup):
    from app.services import session_manufacturer_evidence as bridge
    api, _, _ = setup
    sid = start(setup)['session_id']
    for soc in (40, 45):
        response = api.post(f'/ai-assistant/sessions/{sid}/messages', json={'question': f'SOC is {soc}%'})
        assert response.status_code == 200
    with patch.object(bridge, 'grounded_diagnostic', wraps=bridge.grounded_diagnostic) as lookup:
        detail = api.get(f'/ai-assistant/sessions/{sid}').json()
    assert lookup.call_count == 1
    assert all(message['response_metadata']['manufacturer_evidence']['grounded']
               for message in detail['messages'] if message['role'] == 'assistant')
