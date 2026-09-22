IMPORTANT_TELEMETRY_FIELDS = [
    "pv_voltage",
    "pv_current",
    "pv_power",
    "battery_voltage",
    "battery_current",
    "battery_soc",
    "load_power",
    "temperature",
]

# ML will only be used when at least 75% of the
# important telemetry measurements are available.
MINIMUM_ML_QUALITY_SCORE = 75.0


def assess_data_quality(
    pv_voltage=None,
    pv_current=None,
    pv_power=None,
    battery_voltage=None,
    battery_current=None,
    battery_soc=None,
    load_power=None,
    temperature=None,
):
    """
    Assess the completeness of telemetry data.

    Returns:
        data_quality_score:
            Percentage of important telemetry fields available.

        missing_fields:
            List of missing telemetry fields.

        ml_prediction_available:
            1 when enough data exists for ML prediction.
            0 when data quality is too low.
    """

    values = {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_power,
        "battery_voltage": battery_voltage,
        "battery_current": battery_current,
        "battery_soc": battery_soc,
        "load_power": load_power,
        "temperature": temperature,
    }

    missing_fields = [
        field_name
        for field_name, value in values.items()
        if value is None
    ]

    total_fields = len(
        IMPORTANT_TELEMETRY_FIELDS
    )

    available_fields = (
        total_fields
        - len(missing_fields)
    )

    data_quality_score = round(
        (
            available_fields
            / total_fields
        )
        * 100,
        2,
    )

    ml_prediction_available = int(
        data_quality_score
        >= MINIMUM_ML_QUALITY_SCORE
    )

    return {
        "data_quality_score":
            data_quality_score,

        "missing_fields":
            missing_fields,

        "ml_prediction_available":
            ml_prediction_available,
    }