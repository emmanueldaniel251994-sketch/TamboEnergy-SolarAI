import os
import random
import time

import requests
from dotenv import load_dotenv


# ============================================================
# LOAD CONFIGURATION
# ============================================================

load_dotenv()

DEVICE_API_KEY = os.getenv(
    "DEVICE_API_KEY"
)

SOLARAI_API_URL = os.getenv(
    "SOLARAI_API_URL",
    "http://127.0.0.1:8000",
)

TELEMETRY_URL = (
    f"{SOLARAI_API_URL}/device-telemetry/"
)


if not DEVICE_API_KEY:
    raise RuntimeError(
        "DEVICE_API_KEY is missing from .env"
    )


# ============================================================
# SIMULATOR STATE
# ============================================================

battery_soc = 82.0


# ============================================================
# GENERATE SIMULATED TELEMETRY
# ============================================================

def generate_telemetry():
    global battery_soc

    # Simulate changing sunlight.
    pv_voltage = random.uniform(
        115.0,
        130.0,
    )

    pv_current = random.uniform(
        7.0,
        11.0,
    )

    pv_power = (
        pv_voltage
        * pv_current
    )

    # Simulate household/system load.
    load_power = random.uniform(
        450.0,
        900.0,
    )

    # Simulate battery behaviour.
    battery_voltage = random.uniform(
        50.5,
        52.5,
    )

    battery_current = random.uniform(
        4.0,
        10.0,
    )

    # Slowly change SOC.
    battery_soc += random.uniform(
        -0.5,
        0.5,
    )

    battery_soc = max(
        20.0,
        min(
            battery_soc,
            100.0,
        ),
    )

    # Simulate normal operating temperature.
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
# SEND TELEMETRY
# ============================================================

def send_telemetry(payload):

    headers = {
        "X-Device-API-Key": (
            DEVICE_API_KEY
        ),
        "Content-Type": (
            "application/json"
        ),
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

            print(
                "\nTelemetry sent successfully"
            )

            print(
                f"Record ID: "
                f"{result.get('id')}"
            )

            print(
                f"PV Power: "
                f"{result.get('pv_power')} W"
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
                f"Diagnosis: "
                f"{result.get('final_diagnosis')}"
            )

            print(
                f"ML Confidence: "
                f"{result.get('ml_confidence')}"
            )

        else:

            print(
                "\nTelemetry rejected"
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            print(
                f"Response: "
                f"{response.text}"
            )

    except requests.RequestException as error:

        print(
            "\nUnable to contact SolarAI"
        )

        print(
            f"Error: {error}"
        )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    print(
        "=================================="
    )

    print(
        " TamboEnergy SolarAI Simulator"
    )

    print(
        "=================================="
    )

    print(
        f"Endpoint: {TELEMETRY_URL}"
    )

    print(
        "Transmission interval: 10 seconds"
    )

    print(
        "Press Ctrl+C to stop."
    )

    while True:

        payload = generate_telemetry()

        send_telemetry(
            payload
        )

        time.sleep(10)


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print(
            "\nSimulator stopped."
        )