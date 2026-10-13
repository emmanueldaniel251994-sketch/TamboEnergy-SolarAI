from app.diagnostics.information_extractor import extract_equipment_updates


def test_extract_battery_soc():
    result = extract_equipment_updates("My battery is at 45%")
    assert result["battery_soc_percent"] == 45


def test_extract_pv_voltage():
    result = extract_equipment_updates("PV voltage is 180V")
    assert result["pv_voltage_v"] == 180


def test_extract_charging_power():
    result = extract_equipment_updates("Charging power remains at 0W")
    assert result["pv_power_w"] == 0


def test_extract_multiple_measurements():
    result = extract_equipment_updates(
        "My battery is at 45%, PV voltage is 180V, and charging power is 0W."
    )
    assert result == {
        "battery_soc_percent": 45,
        "pv_voltage_v": 180,
        "pv_power_w": 0,
    }


def test_reject_invalid_soc():
    result = extract_equipment_updates("Battery SOC is 150%")
    assert "battery_soc_percent" not in result


def test_do_not_guess_unlabelled_voltage():
    result = extract_equipment_updates("The reading is 180V")
    assert "pv_voltage_v" not in result
