"""Phase 2G regression tests, using an isolated SQLite DB (never Neon)."""
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.user import User
from app.models.customer import Customer
from app.models.ai_conversation import AIConversationSession, AIConversationMessage
from app.services.ai_sessions import get_owned, run_turn
from app.diagnostics.equipment_profile import EquipmentProfile

@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()

def test_owner_isolation(db):
    s = AIConversationSession(user_id=1, title='Charging', original_complaint='Not charging', equipment_profile={})
    db.add(s)
    db.commit()
    assert get_owned(db, 1, s.id) is not None
    assert get_owned(db, 2, s.id) is None

def test_session_messages_and_profile_persist(db, monkeypatch):
    from app.services import ai_sessions
    s = AIConversationSession(user_id=1, title='Charging', original_complaint='Not charging', equipment_profile={'battery_technology':'LiFePO4'})
    db.add(s)
    db.commit()
    def fake_converse(req):
        assert req.profile.battery_technology == 'LiFePO4'
        assert req.updates['battery_soc_percent'] == 45
        p = req.profile.model_copy(update={'battery_soc_percent':45})
        return SimpleNamespace(profile=p, message='What is the BMS status?', model_dump=lambda mode=None: {'message':'What is the BMS status?'})
    monkeypatch.setattr(ai_sessions, 'converse', fake_converse)
    run_turn(db, s, 'SOC is 45%', {'battery_soc_percent':45})
    db.expire_all()
    assert get_owned(db, 1, s.id).equipment_profile['battery_soc_percent'] == 45
    rows = db.query(AIConversationMessage).filter_by(session_id=s.id).order_by(AIConversationMessage.id).all()
    assert [r.role for r in rows] == ['user', 'assistant']

def test_invalid_profile_update_does_not_write(db):
    s = AIConversationSession(user_id=1, title='Charging', original_complaint='Not charging', equipment_profile={})
    db.add(s)
    db.commit()
    with pytest.raises(ValueError):
        run_turn(db, s, 'Follow-up', {'made_up_field':42})
    assert db.query(AIConversationMessage).count() == 0
