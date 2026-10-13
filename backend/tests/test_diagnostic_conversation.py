from app.diagnostics.conversation import ConversationRequest, converse
from app.diagnostics.equipment_profile import EquipmentProfile


def test_updates_preserve_existing_equipment():
    first = converse(ConversationRequest(question='My solar battery is not charging', profile=EquipmentProfile(rated_capacity_kva=5)))
    second = converse(ConversationRequest(question='The inverter is Growatt model XYZ', profile=first.profile, updates={'inverter_brand':'Growatt','inverter_model':'XYZ'}))
    assert second.profile.rated_capacity_kva == 5
    assert second.profile.inverter_brand == 'Growatt'
    assert second.profile.inverter_model == 'XYZ'


def test_unknown_fields_rejected():
    try:
        converse(ConversationRequest(question='Battery not charging', updates={'made_up_field': 2}))
        assert False
    except ValueError:
        pass


def test_industrial_safety_preserved():
    response = converse(ConversationRequest(question='PV not charging BESS', updates={'rated_capacity_kva':500,'system_type':'industrial'}))
    assert response.safety_level == 'industrial_specialist'
    assert response.sources == []
