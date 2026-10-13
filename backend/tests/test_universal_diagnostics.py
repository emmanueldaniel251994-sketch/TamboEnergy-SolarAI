from app.diagnostics.engine import DiagnosticRequest, diagnose
from app.diagnostics.equipment_profile import EquipmentProfile


def test_unknown_model_does_not_invent_fault_code():
    result = diagnose(DiagnosticRequest(question='What does warning code 61 mean?'))
    assert result.status == 'manual_review_required'
    assert not result.sources
    assert 'not verified' in result.summary


def test_500kva_system_escalates_to_industrial_specialist():
    p = EquipmentProfile(system_type='industrial', rated_capacity_kva=500, ac_voltage_v=415)
    result = diagnose(DiagnosticRequest(question='The solar system output is tripping', profile=p))
    assert result.safety_level == 'industrial_specialist'
    assert any('authorized' in x.lower() for x in result.suggested_solutions)


def test_incomplete_charging_intake_asks_questions():
    p = EquipmentProfile(rated_capacity_kva=5, battery_voltage_v=48, battery_technology='LiFePO4')
    result = diagnose(DiagnosticRequest(question='My inverter is not charging from solar panels', profile=p))
    assert result.status == 'needs_information'
    assert any('model' in q.lower() for q in result.follow_up_questions)
    assert result.possible_causes


def test_emergency_suppresses_normal_troubleshooting():
    result = diagnose(DiagnosticRequest(question='Battery rack is smoking and sparking'))
    assert result.status == 'manual_review_required'
    assert not result.suggested_solutions
    assert 'emergency' in result.summary.lower()


def test_profile_validation():
    from pydantic import ValidationError
    try:
        EquipmentProfile(rated_capacity_kva=-500)
        assert False
    except ValidationError:
        pass


def test_500kva_not_assumed_high_voltage():
    p = EquipmentProfile(rated_capacity_kva=500, ac_voltage_v=415)
    assert p.industrial_risk
    assert p.ac_voltage_v == 415
