import hashlib
import hmac
import json
import os
import random
import time
import uuid

import requests
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DEVICE_API_KEY = os.getenv("DEVICE_API_KEY")

SOLARAI_API_URL = os.getenv(
    "SOLARAI_API_URL",
    "http://127.0.0.1:8000",
)

TELEMETRY_URL = (
    f"{SOLARAI_API_URL}/device-telemetry/"
)

TRANSMISSION_INTERVAL = 10


if not DEVICE_API_KEY:
    raise RuntimeError(
        "DEVICE_API_KEY is missing from .env"
    )


# ============================================================
# SIMULATOR STATE
# ============================================================

battery_soc = 82.0


# ============================================================
# SCENARIOS
# ============================================================

SCENARIOS = {
    "1": "normal",
    "2": "high_temperature",
    "3": "overheating",
    "4": "low_battery",
    "5": "critical_low_battery",
    "6": "battery_undervoltage",
    "7": "battery_overvoltage",
    "8": "high_load",
    "9": "inverter_error",
}


def show_menu():

    print("\n==================================")
    print(" SolarAI Device Fault Simulator")
    print("==================================")

    print("1 - Normal operation")
    print("2 - High temperature")
    print("3 - Critical overheating")
    print("4 - Low battery")
    print("5 - Critical low battery")
    print("6 - Battery undervoltage")
    print("7 - Battery overvoltage")
    print("8 - High load")
    print("9 - Inverter error")
    print("0 - Exit")


# ============================================================
# BASE TELEMETRY
# ============================================================

def generate_normal_telemetry():

    global battery_soc

    pv_voltage = random.uniform(
        115.0,
        130.0,
    )

    pv_current = random.uniform(
        7.0,
        11.0,
    )

    pv_power = (
        pv_voltage * pv_current
    )

    battery_voltage = random.uniform(
        50.5,
        52.5,
    )

    battery_current = random.uniform(
        4.0,
        10.0,
    )

    battery_soc += random.uniform(
        -0.5,
        0.5,
    )

    battery_soc = max(
        25.0,
        min(
            battery_soc,
            100.0,
        ),
    )

    load_power = random.uniform(
        450.0,
        900.0,
    )

    temperature = random.uniform(
        28.0,
        38.0,
    )

    return {
        "pv_voltage": round(
            pv_voltage,
            2,
        ),
        "pv_current": round(
            pv_current,
            2,
        ),
        "pv_power": round(
            pv_power,
            2,
        ),
        "battery_voltage": round(
            battery_voltage,
            2,
        ),
        "battery_current": round(
            battery_current,
            2,
        ),
        "battery_soc": round(
            battery_soc,
            2,
        ),
        "load_power": round(
            load_power,
            2,
        ),
        "temperature": round(
            temperature,
            2,
        ),
        "error_code": None,
    }


# ============================================================
# APPLY FAULT SCENARIO
# ============================================================

def apply_scenario(
    payload,
    scenario,
):

    if scenario == "normal":
        return payload

    if scenario == "high_temperature":
        payload["temperature"] = 55.0

    elif scenario == "overheating":
        payload["temperature"] = 65.0

    elif scenario == "low_battery":
        payload["battery_soc"] = 15.0

    elif scenario == "critical_low_battery":
        payload["battery_soc"] = 5.0

    elif scenario == "battery_undervoltage":
        payload["battery_voltage"] = 44.0

    elif scenario == "battery_overvoltage":
        payload["battery_voltage"] = 58.0

    elif scenario == "high_load":
        payload["load_power"] = 3500.0

    elif scenario == "inverter_error":
        payload["error_code"] = "E01"

    return payload


# ============================================================
# REQUEST SIGNING
# ============================================================


def create_signature(payload, timestamp, nonce):
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    payload_hash = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    message = f"v1.{timestamp}.{nonce}.{payload_hash}"
    return hmac.new(
        DEVICE_API_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ============================================================
# SEND TELEMETRY
# ============================================================

def send_telemetry(
    payload,
    scenario,
):

    # Each logical reading receives a stable event ID. If a gateway retries
    # the same event after a network interruption it should reuse this ID.
    payload.setdefault("event_id", uuid.uuid4().hex)

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    signature = create_signature(payload, timestamp, nonce)

    headers = {
        "X-Device-API-Key": DEVICE_API_KEY,
        "X-Device-Timestamp": timestamp,
        "X-Device-Nonce": nonce,
        "X-Device-Signature": signature,
        "Content-Type": "application/json",
    }

    try:

        response = requests.post(
            TELEMETRY_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:

            result = response.json()

            print("\n----------------------------------")
            print("Telemetry sent successfully")
            print("----------------------------------")

            print(
                f"Scenario: {scenario}"
            )

            print(
                f"Record ID: {result.get('id')}"
            )

            print(
                f"PV Power: "
                f"{result.get('pv_power')} W"
            )

            print(
                f"Battery Voltage: "
                f"{result.get('battery_voltage')} V"
            )

            print(
                f"Battery SOC: "
                f"{result.get('battery_soc')}%"
            )

            print(
                f"Load: "
                f"{result.get('load_power')} W"
            )

            print(
                f"Temperature: "
                f"{result.get('temperature')} C"
            )

            print(
                f"Error Code: "
                f"{result.get('error_code')}"
            )

            print(
                f"Status: "
                f"{result.get('status')}"
            )

            print(
                f"Rule Fault: "
                f"{result.get('fault_type')}"
            )

            print(
                f"Severity: "
                f"{result.get('fault_severity')}"
            )

            print(
                f"ML Prediction: "
                f"{result.get('ml_prediction')}"
            )

            confidence = result.get(
                "ml_confidence"
            )

            print(
                f"ML Confidence: {confidence}"
            )

            print(
                f"Agreement: "
                f"{result.get('prediction_agreement')}"
            )

            print(
                f"Final Diagnosis: "
                f"{result.get('final_diagnosis')}"
            )

            print(
                f"Needs Review: "
                f"{result.get('needs_review')}"
            )

            return True

        print("\nTelemetry rejected")

        print(
            f"HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"Response: "
            f"{response.text}"
        )

        return False

    except requests.RequestException as error:

        print(
            "\nUnable to contact SolarAI"
        )

        print(
            f"Error: {error}"
        )

        return False


# ============================================================
# RUN SELECTED SCENARIO
# ============================================================

def run_scenario(
    scenario,
):

    print(
        f"\nRunning scenario: {scenario}"
    )

    print(
        "Press Ctrl+C to return to the menu."
    )

    while True:

        payload = generate_normal_telemetry()

        payload = apply_scenario(
            payload,
            scenario,
        )

        send_telemetry(
            payload,
            scenario,
        )

        time.sleep(
            TRANSMISSION_INTERVAL
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\nTamboEnergy SolarAI "
        "Device Simulator"
    )

    print(
        f"API: {TELEMETRY_URL}"
    )

    while True:

        show_menu()

        choice = input(
            "\nSelect scenario: "
        ).strip()

        if choice == "0":

            print(
                "\nSimulator stopped."
            )

            break

        scenario = SCENARIOS.get(
            choice
        )

        if not scenario:

            print(
                "\nInvalid selection."
            )

            continue

        try:

            run_scenario(
                scenario
            )

        except KeyboardInterrupt:

            print(
                "\n\nScenario stopped."
            )

            print(
                "Returning to menu..."
            )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print(
            "\nSimulator stopped."
        )