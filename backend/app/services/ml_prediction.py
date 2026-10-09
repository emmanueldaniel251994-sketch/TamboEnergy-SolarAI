import os

import joblib
import pandas as pd


# ============================================================
# MODEL FILE PATHS
# ============================================================

PROJECT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
    )
)

MODEL_PATH = os.path.join(
    PROJECT_DIR,
    "ml",
    "fault_model.joblib",
)

ENCODER_PATH = os.path.join(
    PROJECT_DIR,
    "ml",
    "label_encoder.joblib",
)


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(ENCODER_PATH)


# ============================================================
# REQUIRED ML FEATURES
# ============================================================

FEATURES = [
    "pv_voltage",
    "pv_current",
    "pv_power",
    "battery_voltage",
    "battery_current",
    "battery_soc",
    "load_power",
    "temperature",
    "has_error_code",
]


# ============================================================
# HELPER FUNCTION
# ============================================================

def safe_number(value, default=0.0):
    """
    Convert telemetry value to float.

    Missing or invalid values are replaced with the
    supplied default so that the ML model does not crash.
    """

    if value is None:
        return default

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


# ============================================================
# ML FAULT PREDICTION
# ============================================================

def predict_fault(
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

    # --------------------------------------------------------
    # HANDLE MISSING VALUES
    # --------------------------------------------------------

    pv_voltage = safe_number(pv_voltage)
    pv_current = safe_number(pv_current)

    # If PV power is missing, calculate it when possible.
    if pv_power is None:
        pv_power = pv_voltage * pv_current
    else:
        pv_power = safe_number(pv_power)

    battery_voltage = safe_number(
        battery_voltage
    )

    battery_current = safe_number(
        battery_current
    )

    battery_soc = safe_number(
        battery_soc
    )

    load_power = safe_number(
        load_power
    )

    temperature = safe_number(
        temperature
    )

    has_error_code = (
        1 if error_code else 0
    )

    # --------------------------------------------------------
    # CREATE MODEL INPUT
    # --------------------------------------------------------

    input_data = {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_power,
        "battery_voltage": battery_voltage,
        "battery_current": battery_current,
        "battery_soc": battery_soc,
        "load_power": load_power,
        "temperature": temperature,
        "has_error_code": has_error_code,
    }

    data = pd.DataFrame(
        [input_data],
        columns=FEATURES,
    )

    # --------------------------------------------------------
    # MAKE PREDICTION
    # --------------------------------------------------------

    try:

        prediction = model.predict(
            data
        )[0]

        probabilities = model.predict_proba(
            data
        )[0]

        confidence = float(
            max(probabilities)
        )

        fault_name = (
            label_encoder.inverse_transform(
                [prediction]
            )[0]
        )

        return {
            "predicted_fault": fault_name,
            "confidence": confidence,
            "prediction_available": True,
        }

    except Exception as exc:

        # ----------------------------------------------------
        # FAIL SAFELY
        # ----------------------------------------------------
        #
        # ML failure should not stop telemetry from being
        # recorded or stop the deterministic safety rules.
        # ----------------------------------------------------

        print(
            f"ML prediction failed: {exc}"
        )

        return {
            "predicted_fault": None,
            "confidence": 0.0,
            "prediction_available": False,
        }