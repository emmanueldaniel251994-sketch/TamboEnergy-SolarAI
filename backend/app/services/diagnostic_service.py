def generate_diagnostic(
    diagnosis: str,
    severity: str | None = None,
    confidence: float | None = None,
    needs_review: int = 0,
):
    """
    Convert a SolarAI fault diagnosis into a human-readable
    explanation and safe recommended action.
    """

    diagnostics = {

        # ====================================================
        # NORMAL
        # ====================================================

        "normal": {
            "title": "Solar system operating normally",
            "explanation": (
                "The available telemetry does not currently "
                "indicate a known solar system fault."
            ),
            "possible_causes": [],
            "recommended_action": (
                "Continue normal operation and routine "
                "system monitoring."
            ),
            "priority": "low",
        },

        # ====================================================
        # LOW BATTERY
        # ====================================================

        "low_battery": {
            "title": "Low battery state of charge",
            "explanation": (
                "The battery state of charge is below the "
                "recommended operating level."
            ),
            "possible_causes": [
                "Insufficient solar charging",
                "High energy consumption",
                "Extended operation without adequate charging",
                "Reduced battery performance",
            ],
            "recommended_action": (
                "Reduce unnecessary loads and monitor the "
                "battery charging process. If the battery does "
                "not recover after adequate charging conditions, "
                "have the battery and charging system inspected "
                "by a qualified technician."
            ),
            "priority": "medium",
        },

        # ====================================================
        # CRITICAL LOW BATTERY
        # ====================================================

        "critical_low_battery": {
            "title": "Critically low battery",
            "explanation": (
                "The battery state of charge has reached a "
                "critically low level."
            ),
            "possible_causes": [
                "Heavy or prolonged load",
                "Insufficient solar generation",
                "Charging system problem",
                "Possible battery degradation",
            ],
            "recommended_action": (
                "Reduce non-essential loads and avoid unnecessary "
                "battery discharge. The charging system and battery "
                "condition should be checked by a qualified "
                "technician if normal charging does not restore "
                "the battery."
            ),
            "priority": "critical",
        },

        # ====================================================
        # BATTERY UNDERVOLTAGE
        # ====================================================

        "battery_undervoltage": {
            "title": "Battery undervoltage detected",
            "explanation": (
                "The measured battery voltage is below the "
                "expected operating range."
            ),
            "possible_causes": [
                "Deep battery discharge",
                "Insufficient charging",
                "Battery deterioration",
                "Abnormal load demand",
            ],
            "recommended_action": (
                "Limit non-essential loads and have the battery "
                "voltage, charging performance, and battery "
                "condition assessed if the condition persists."
            ),
            "priority": "high",
        },

        # ====================================================
        # BATTERY OVERVOLTAGE
        # ====================================================

        "battery_overvoltage": {
            "title": "Battery overvoltage detected",
            "explanation": (
                "The measured battery voltage is above the "
                "expected operating range."
            ),
            "possible_causes": [
                "Charging control problem",
                "Incorrect charging configuration",
                "Battery management system issue",
                "Abnormal charger behaviour",
            ],
            "recommended_action": (
                "Treat this as a potentially serious charging "
                "condition. Avoid attempting internal electrical "
                "repairs and have the charging system inspected "
                "by a qualified technician."
            ),
            "priority": "critical",
        },

        # ====================================================
        # HIGH LOAD
        # ====================================================

        "high_load": {
            "title": "High electrical load detected",
            "explanation": (
                "The connected load is unusually high and may "
                "be approaching or exceeding the intended system "
                "operating range."
            ),
            "possible_causes": [
                "Too many appliances operating simultaneously",
                "High-power appliance connected",
                "Unexpected increase in energy demand",
            ],
            "recommended_action": (
                "Reduce non-essential loads and monitor system "
                "performance. Persistent overload conditions "
                "should be assessed by a qualified technician."
            ),
            "priority": "high",
        },

        # ====================================================
        # HIGH TEMPERATURE
        # ====================================================

        "high_temperature": {
            "title": "High system temperature",
            "explanation": (
                "The monitored equipment temperature is above "
                "the preferred operating range."
            ),
            "possible_causes": [
                "Poor ventilation",
                "High ambient temperature",
                "Heavy system load",
                "Cooling problem",
            ],
            "recommended_action": (
                "Reduce unnecessary load and ensure the equipment "
                "area is not obstructed. If high temperature "
                "continues, have the system inspected by a "
                "qualified technician."
            ),
            "priority": "high",
        },

        # ====================================================
        # OVERHEATING
        # ====================================================

        "overheating": {
            "title": "Possible system overheating",
            "explanation": (
                "The equipment temperature has reached a level "
                "that may affect safe and reliable operation."
            ),
            "possible_causes": [
                "Ventilation failure",
                "Excessive load",
                "Cooling system problem",
                "High environmental temperature",
                "Equipment fault",
            ],
            "recommended_action": (
                "Treat the condition as urgent. Reduce exposure "
                "to continued heavy operation where this can be "
                "done safely and arrange inspection by a qualified "
                "solar/electrical technician."
            ),
            "priority": "critical",
        },

        # ====================================================
        # LOW PV GENERATION
        # ====================================================

        "low_pv_generation": {
            "title": "Low solar generation",
            "explanation": (
                "PV power generation is lower than expected "
                "for the monitored operating condition."
            ),
            "possible_causes": [
                "Low sunlight",
                "Panel shading",
                "Dirty solar panels",
                "PV system performance problem",
                "Weather conditions",
            ],
            "recommended_action": (
                "Monitor PV production under good sunlight "
                "conditions. Check for obvious shading or surface "
                "obstruction without accessing hazardous wiring. "
                "Persistent low generation should be investigated "
                "by a qualified technician."
            ),
            "priority": "medium",
        },

        # ====================================================
        # INVERTER ERROR
        # ====================================================

        "inverter_error": {
            "title": "Inverter error detected",
            "explanation": (
                "The telemetry contains an inverter or equipment "
                "error indication."
            ),
            "possible_causes": [
                "Inverter protection event",
                "Input or output abnormality",
                "Battery-related condition",
                "Internal inverter fault",
                "Communication or sensor issue",
            ],
            "recommended_action": (
                "Record the inverter error code and consult the "
                "manufacturer's documentation or a qualified "
                "technician. Do not open or repair energized "
                "inverter equipment."
            ),
            "priority": "high",
        },
    }

    # ========================================================
    # GET DIAGNOSTIC
    # ========================================================

    result = diagnostics.get(diagnosis)

    # Unknown diagnosis
    if result is None:

        result = {
            "title": "Unclassified solar system condition",
            "explanation": (
                "SolarAI detected a condition that does not yet "
                "have a predefined diagnostic explanation."
            ),
            "possible_causes": [],
            "recommended_action": (
                "Review the telemetry and have the condition "
                "assessed by a qualified technician if abnormal "
                "operation continues."
            ),
            "priority": severity or "unknown",
        }

    # Copy so the original dictionary is not modified
    result = result.copy()

    # ========================================================
    # ADD ML INFORMATION
    # ========================================================

    result["diagnosis"] = diagnosis

    result["confidence"] = confidence

    result["needs_review"] = needs_review

    # ========================================================
    # TECHNICIAN REVIEW MESSAGE
    # ========================================================

    if needs_review:

        result["review_message"] = (
            "The rule-based detector and machine-learning model "
            "did not fully agree. Technician review is recommended."
        )

    else:

        result["review_message"] = (
            "No rule/ML disagreement was detected for this record."
        )

    return result