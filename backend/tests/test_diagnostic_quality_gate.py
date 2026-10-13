from app.diagnostics.engine import DiagnosticRequest, diagnose
from app.diagnostics.equipment_profile import EquipmentProfile
from app.diagnostics.quality_gate import diagnose_checked, review

def sample(**changes):
    return DiagnosticRequest(question='My solar panels are in sunlight but the battery is not charging',
                             profile=EquipmentProfile(**changes))

def test_pv_charging_keeps_relevant_diagnosis():
    output = diagnose_checked(sample(inverter_brand='Growatt', inverter_model='SPF 5000 ES',
                                    pv_voltage_v=180, pv_power_w=0, battery_voltage_v=51.2))
    assert output.passed
    assert any('pv' in x.lower() or 'mppt' in x.lower() for x in output.result.recommended_checks)

def test_unrelated_diagnosis_is_withheld():
    request = sample()
    result = diagnose(request)
    result.possible_causes = ['Poor generator power quality']
    result.recommended_checks = ['Check generator frequency']
    result.suggested_solutions = []
    output = review(request, result)
    assert not output.passed
    assert output.result.status == 'manual_review_required'
    assert output.result.suggested_solutions == []

def test_unsafe_action_is_withheld():
    request = sample()
    result = diagnose(request)
    result.suggested_solutions = ['Bypass protection to charge battery']
    assert not review(request, result).passed

def test_unverified_source_is_withheld():
    request = sample()
    result = diagnose(request)
    result.sources = [{'title': 'Unknown manual'}]
    assert not review(request, result).passed

def test_industrial_safety_escalation():
    request = sample(system_type='industrial', rated_capacity_kva=500)
    output = diagnose_checked(request)
    assert output.passed
    assert output.result.safety_level == 'industrial_specialist'

def test_industrial_safety_downgrade_is_withheld():
    request = sample(system_type='industrial', rated_capacity_kva=500)
    result = diagnose(request)
    result.safety_level = 'standard'
    assert not review(request, result).passed
