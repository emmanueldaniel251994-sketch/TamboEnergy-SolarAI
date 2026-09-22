def calculate_health_score(
    status=None,
    battery_soc=None,
    temperature=None,
    fault_type=None,
    final_diagnosis=None,
    needs_review=0,
):
    score = 100

    diagnosis = (
        final_diagnosis
        or fault_type
        or "normal"
    )

    # Battery condition
    if battery_soc is not None:
        if battery_soc <= 10:
            score -= 35
        elif battery_soc <= 20:
            score -= 20
        elif battery_soc <= 30:
            score -= 10

    # Temperature condition
    if temperature is not None:
        if temperature >= 60:
            score -= 35
        elif temperature >= 50:
            score -= 20
        elif temperature >= 45:
            score -= 10

    # Diagnosis condition
    critical_faults = {
        "critical_low_battery",
        "overheating",
    }

    high_faults = {
        "battery_undervoltage",
        "battery_overvoltage",
        "inverter_error",
        "high_temperature",
        "high_load",
    }

    medium_faults = {
        "low_battery",
        "low_pv_generation",
    }

    if diagnosis in critical_faults:
        score -= 30

    elif diagnosis in high_faults:
        score -= 20

    elif diagnosis in medium_faults:
        score -= 10

    # AI/rule disagreement
    if needs_review == 1:
        score -= 15

    # General telemetry status
    if status == "fault":
        score -= 10
    elif status == "warning":
        score -= 5

    # Never allow score below 0
    score = max(0, min(100, score))

    # Convert score to readable health status
    if score >= 85:
        health_status = "healthy"

    elif score >= 65:
        health_status = "warning"

    elif score >= 40:
        health_status = "poor"

    else:
        health_status = "critical"

    return {
        "score": score,
        "health_status": health_status,
    }