"""Saved conversation API contracts with an isolated DB and authenticated users."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.security import get_current_user


@pytest.fixture
def api():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def database():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role='customer', is_active=1)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def start(api):
    response = api.post('/ai-assistant/sessions', json={
        'question': 'My inverter is not charging from solar panels',
        'profile': {'inverter_brand': 'Reported brand', 'battery_technology': 'LiFePO4'},
    })
    assert response.status_code == 201, response.text
    return response.json()['session_id']


def test_create_list_and_reopen(api):
    sid = start(api)
    cases = api.get('/ai-assistant/sessions').json()
    assert [case['id'] for case in cases] == [sid]
    detail = api.get(f'/ai-assistant/sessions/{sid}').json()
    assert [message['role'] for message in detail['messages']] == ['user', 'assistant']
    assert detail['session']['equipment_profile']['inverter_brand'] == 'Reported brand'
    assert 'safety_notice' in detail['messages'][1]['response_metadata']


def test_followup_persists_readings_and_original_text(api):
    sid = start(api)
    response = api.post(f'/ai-assistant/sessions/{sid}/messages', json={'question': 'SOC is 45%'})
    assert response.status_code == 200, response.text
    detail = api.get(f'/ai-assistant/sessions/{sid}').json()
    assert detail['session']['equipment_profile']['battery_soc_percent'] == 45
    assert detail['messages'][-2]['content'] == 'SOC is 45%'
    assert len(detail['messages']) == 4


def test_explicit_edited_reading_wins(api):
    sid = start(api)
    response = api.post(f'/ai-assistant/sessions/{sid}/messages', json={
        'question': 'SOC is 45%', 'updates': {'battery_soc_percent': 52},
    })
    assert response.status_code == 200, response.text
    assert response.json()['response']['profile']['battery_soc_percent'] == 52


@pytest.mark.parametrize('updates', [{'battery_soc_percent': 101}, {'unknown_field': 1}])
def test_invalid_updates_leave_history_unchanged(api, updates):
    sid = start(api)
    response = api.post(f'/ai-assistant/sessions/{sid}/messages', json={'question': 'New reading', 'updates': updates})
    assert response.status_code == 422
    assert len(api.get(f'/ai-assistant/sessions/{sid}').json()['messages']) == 2


def test_other_user_cannot_read_or_continue_case(api):
    sid = start(api)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, role='customer', is_active=1)
    assert api.get('/ai-assistant/sessions').json() == []
    assert api.get(f'/ai-assistant/sessions/{sid}').status_code == 404
    assert api.post(f'/ai-assistant/sessions/{sid}/messages', json={'question': 'SOC is 45%'}).status_code == 404


def test_blank_question_rejected(api):
    assert api.post('/ai-assistant/sessions', json={'question': ''}).status_code == 422
    assert api.get('/ai-assistant/sessions').json() == []
