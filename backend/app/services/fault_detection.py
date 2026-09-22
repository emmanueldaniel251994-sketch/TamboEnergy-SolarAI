def detect_fault(
    pv_voltage=None,
    pv_current=None,
    pv_power=None,
    battery_voltage=None,
    battery_current=None,
    battery_soc=None,
    load_power=None,
    temperature=None,
    error_code=None,
):
    """
    Rule-based solar fault detection.

    Returns:
        {
            "fault_type": str | None,
            "fault_severity": str | None,
            "status": str
        }
    """

    # --------------------------------------------------------
    # INVERTER / DEVICE ERROR
    # --------------------------------------------------------

    if error_code:
        return {
            "fault_type": "inverter_error",
            "fault_severity": "high",
            "status": "fault",
        }

    # --------------------------------------------------------
    # CRITICAL LOW BATTERY
    # --------------------------------------------------------

    if battery_soc is not None and battery_soc <= 10:
        return {
            "fault_type": "critical_low_battery",
            "fault_severity": "critical",
            "status": "fault",
        }

    # --------------------------------------------------------
    # LOW BATTERY
    # --------------------------------------------------------

    if battery_soc is not None and battery_soc <= 20:
        return {
            "fault_type": "low_battery",
            "fault_severity": "medium",
            "status": "warning",
        }

    # --------------------------------------------------------
    # BATTERY UNDERVOLTAGE
    # --------------------------------------------------------

    if battery_voltage is not None and battery_voltage < 46:
        return {
            "fault_type": "battery_undervoltage",
            "fault_severity": "high",
            "status": "fault",
        }

    # --------------------------------------------------------
    # BATTERY OVERVOLTAGE
    # --------------------------------------------------------

    if battery_voltage is not None and battery_voltage > 56:
        return {
            "fault_type": "battery_overvoltage",
            "fault_severity": "high",
            "status": "fault",
        }

    # --------------------------------------------------------
    # HIGH TEMPERATURE
    # --------------------------------------------------------

    if temperature is not None and temperature >= 60:
        return {
            "fault_type": "overheating",
            "fault_severity": "critical",
            "status": "fault",
        }

    if temperature is not None and temperature >= 50:
        return {
            "fault_type": "high_temperature",
            "fault_severity": "high",
            "status": "warning",
        }

    # --------------------------------------------------------
    # HIGH LOAD
    # --------------------------------------------------------

    if load_power is not None and load_power >= 3000:
        return {
            "fault_type": "high_load",
            "fault_severity": "high",
            "status": "warning",
        }

    # --------------------------------------------------------
    # LOW PV GENERATION
    # --------------------------------------------------------

    if pv_power is not None and pv_power < 100:
        return {
            "fault_type": "low_pv_generation",
            "fault_severity": "medium",
            "status": "warning",
        }

    # --------------------------------------------------------
    # NORMAL CONDITION
    # --------------------------------------------------------

    return {
        "fault_type": "normal",
        "fault_severity": "none",
        "status": "normal",
    }