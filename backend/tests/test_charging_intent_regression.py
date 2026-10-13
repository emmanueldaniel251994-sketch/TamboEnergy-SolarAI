from app.diagnostics.engine import DiagnosticRequest, diagnose
from app.diagnostics.equipment_profile import EquipmentProfile
from app.diagnostics.conversation import ConversationRequest, converse


def test_pv_charging_priority_over_incidental_generator():
    profile = EquipmentProfile(symptoms='Battery not charging despite sunlight', pv_voltage_v=180, pv_power_w=0, grid_or_generator='unknown')
    result = diagnose(DiagnosticRequest(question='Battery not charging from solar; grid or generator unknown', profile=profile))
    assert 'MPPT' in ' '.join(result.possible_causes)
    assert 'generator power quality' not in ' '.join(result.possible_causes).lower()


def test_follow_up_stays_with_solar_charging():
    initial = converse(ConversationRequest(question='My solar panels are not charging my battery', profile=EquipmentProfile(rated_capacity_kva=5, symptoms='Battery not charging despite sunlight')))
    later = converse(ConversationRequest(question='Growatt SPF 5000 ES, PV 180V, power 0W', profile=initial.profile, updates={'inverter_brand':'Growatt','inverter_model':'SPF 5000 ES','pv_voltage_v':180,'pv_power_w':0}))
    assert any('MPPT' in cause for cause in later.possible_causes)
    assert not any('generator' in cause.lower() for cause in later.possible_causes)


def test_actual_generator_waveform_stays_ac_input():
    result = diagnose(DiagnosticRequest(question='Generator waveform abnormal and AC input rejected'))
    assert any('generator' in cause.lower() for cause in result.possible_causes)


def test_industrial_safety_kept():
    result = diagnose(DiagnosticRequest(question='500kVA solar PV not charging battery', profile=EquipmentProfile(rated_capacity_kva=500,system_type='industrial')))
    assert result.safety_level == 'industrial_specialist'
