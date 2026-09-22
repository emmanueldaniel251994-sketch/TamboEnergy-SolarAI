import random
import sqlite3
from datetime import datetime, timezone


DB_NAME = "tamboenergy_solarai.db"

SOLAR_SYSTEM_ID = 1

NUMBER_OF_RECORDS = 500


def generate_normal():
    pv_voltage = random.uniform(140, 220)
    pv_current = random.uniform(3, 10)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(49, 54),
        "battery_current": random.uniform(-10, 25),
        "battery_soc": random.uniform(35, 100),
        "load_power": random.uniform(200, 1800),
        "temperature": random.uniform(25, 42),
        "error_code": None,
        "status": "normal",
        "fault_type": None,
        "fault_severity": None,
    }


def generate_low_battery():
    pv_voltage = random.uniform(120, 180)
    pv_current = random.uniform(1, 6)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(46.5, 49),
        "battery_current": random.uniform(-30, -5),
        "battery_soc": random.uniform(11, 20),
        "load_power": random.uniform(400, 1600),
        "temperature": random.uniform(28, 42),
        "error_code": None,
        "status": "warning",
        "fault_type": "low_battery",
        "fault_severity": "high",
    }


def generate_critical_low_battery():
    pv_voltage = random.uniform(100, 170)
    pv_current = random.uniform(0.5, 5)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(45.5, 47),
        "battery_current": random.uniform(-35, -8),
        "battery_soc": random.uniform(2, 10),
        "load_power": random.uniform(300, 1400),
        "temperature": random.uniform(28, 40),
        "error_code": None,
        "status": "fault",
        "fault_type": "critical_low_battery",
        "fault_severity": "critical",
    }


def generate_overheating():
    pv_voltage = random.uniform(130, 210)
    pv_current = random.uniform(3, 9)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(49, 54),
        "battery_current": random.uniform(0, 25),
        "battery_soc": random.uniform(40, 95),
        "load_power": random.uniform(800, 2500),
        "temperature": random.uniform(60, 75),
        "error_code": None,
        "status": "fault",
        "fault_type": "overheating",
        "fault_severity": "critical",
    }


def generate_high_temperature():
    pv_voltage = random.uniform(130, 210)
    pv_current = random.uniform(3, 9)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(49, 54),
        "battery_current": random.uniform(0, 25),
        "battery_soc": random.uniform(40, 95),
        "load_power": random.uniform(800, 2200),
        "temperature": random.uniform(50, 59.9),
        "error_code": None,
        "status": "warning",
        "fault_type": "high_temperature",
        "fault_severity": "high",
    }


def generate_high_load():
    pv_voltage = random.uniform(140, 220)
    pv_current = random.uniform(4, 10)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(48.5, 53),
        "battery_current": random.uniform(-25, 30),
        "battery_soc": random.uniform(35, 90),
        "load_power": random.uniform(3001, 4500),
        "temperature": random.uniform(30, 48),
        "error_code": None,
        "status": "warning",
        "fault_type": "high_load",
        "fault_severity": "high",
    }


def generate_low_pv():
    pv_voltage = random.uniform(20, 90)
    pv_current = random.uniform(0.1, 1.0)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(48, 53),
        "battery_current": random.uniform(-15, 10),
        "battery_soc": random.uniform(30, 90),
        "load_power": random.uniform(200, 1200),
        "temperature": random.uniform(25, 40),
        "error_code": None,
        "status": "warning",
        "fault_type": "low_pv_generation",
        "fault_severity": "medium",
    }


def generate_battery_undervoltage():
    pv_voltage = random.uniform(100, 180)
    pv_current = random.uniform(1, 6)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(42, 45.9),
        "battery_current": random.uniform(-30, -5),
        "battery_soc": random.uniform(10, 35),
        "load_power": random.uniform(400, 1500),
        "temperature": random.uniform(25, 42),
        "error_code": None,
        "status": "fault",
        "fault_type": "battery_undervoltage",
        "fault_severity": "critical",
    }


def generate_battery_overvoltage():
    pv_voltage = random.uniform(160, 240)
    pv_current = random.uniform(4, 10)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(58.1, 62),
        "battery_current": random.uniform(5, 30),
        "battery_soc": random.uniform(85, 100),
        "load_power": random.uniform(300, 1400),
        "temperature": random.uniform(28, 45),
        "error_code": None,
        "status": "fault",
        "fault_type": "battery_overvoltage",
        "fault_severity": "critical",
    }


def generate_inverter_error():
    pv_voltage = random.uniform(100, 220)
    pv_current = random.uniform(1, 10)

    return {
        "pv_voltage": pv_voltage,
        "pv_current": pv_current,
        "pv_power": pv_voltage * pv_current,
        "battery_voltage": random.uniform(47, 54),
        "battery_current": random.uniform(-20, 25),
        "battery_soc": random.uniform(20, 95),
        "load_power": random.uniform(200, 2200),
        "temperature": random.uniform(25, 50),
        "error_code": random.choice(
            [
                "E01",
                "E02",
                "COMM01",
                "OVP01",
                "TEMP01"
            ]
        ),
        "status": "fault",
        "fault_type": "inverter_error",
        "fault_severity": "critical",
    }


GENERATORS = [
    generate_normal,
    generate_low_battery,
    generate_critical_low_battery,
    generate_overheating,
    generate_high_temperature,
    generate_high_load,
    generate_low_pv,
    generate_battery_undervoltage,
    generate_battery_overvoltage,
    generate_inverter_error,
]


def insert_record(cursor, record):
    cursor.execute(
        """
        INSERT INTO telemetry (
            solar_system_id,
            pv_voltage,
            pv_current,
            pv_power,
            battery_voltage,
            battery_current,
            battery_soc,
            load_power,
            temperature,
            error_code,
            fault_type,
            fault_severity,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            SOLAR_SYSTEM_ID,
            record["pv_voltage"],
            record["pv_current"],
            record["pv_power"],
            record["battery_voltage"],
            record["battery_current"],
            record["battery_soc"],
            record["load_power"],
            record["temperature"],
            record["error_code"],
            record["fault_type"],
            record["fault_severity"],
            record["status"],
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def main():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    system = cursor.execute(
        "SELECT id FROM solar_systems WHERE id = ?",
        (SOLAR_SYSTEM_ID,),
    ).fetchone()

    if system is None:
        conn.close()

        print(
            f"Solar system {SOLAR_SYSTEM_ID} does not exist."
        )
        print(
            "Create the solar system first or change SOLAR_SYSTEM_ID."
        )

        return

    print("================================")
    print("TAMBOENERGY TELEMETRY SIMULATOR")
    print("================================")

    print(
        f"Generating {NUMBER_OF_RECORDS} records..."
    )

    counts = {}

    for _ in range(NUMBER_OF_RECORDS):
        generator = random.choice(GENERATORS)

        record = generator()

        insert_record(
            cursor,
            record
        )

        label = (
            record["fault_type"]
            if record["fault_type"]
            else "normal"
        )

        counts[label] = (
            counts.get(label, 0) + 1
        )

    conn.commit()
    conn.close()

    print("\nSimulation complete.")

    print(
        f"Records inserted: {NUMBER_OF_RECORDS}"
    )

    print("\nClass distribution:")

    for label, count in sorted(
        counts.items()
    ):
        print(
            f"{label:30s} {count}"
        )


if __name__ == "__main__":
    main()