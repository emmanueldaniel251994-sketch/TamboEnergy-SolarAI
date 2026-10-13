from app.diagnostics.conversation import _refine_questions
from app.diagnostics.equipment_profile import EquipmentProfile


def test_known_chemistry_not_reasked():
    p = EquipmentProfile(battery_technology='LiFePO4')
    q = _refine_questions(['What battery chemistry, manufacturer and exact model are installed?'], p)
    assert len(q) == 1
    assert 'chemistry' not in q[0].lower()
    assert 'manufacturer' in q[0].lower() and 'model' in q[0].lower()


def test_all_battery_identity_known_removes_redundant_question():
    p = EquipmentProfile(battery_technology='LiFePO4', battery_brand='Example', battery_model='ABC')
    assert _refine_questions(['What battery chemistry, manufacturer and exact model are installed?'], p) == []


def test_soc_question_removed_if_soc_provided():
    p = EquipmentProfile(battery_soc_percent=80)
    assert _refine_questions(['What battery state of charge (SOC) does the battery or BMS display?'], p) == []


def test_unknown_soc_still_requested():
    p = EquipmentProfile()
    q = ['What battery state of charge (SOC) does the battery or BMS display?']
    assert _refine_questions(q, p) == q


def test_bms_warning_question_preserved():
    p = EquipmentProfile(battery_technology='LiFePO4', pv_voltage_v=180, pv_power_w=0)
    q = ['Does the inverter or BMS show a charge-inhibit warning or error code?']
    assert _refine_questions(q, p) == q
