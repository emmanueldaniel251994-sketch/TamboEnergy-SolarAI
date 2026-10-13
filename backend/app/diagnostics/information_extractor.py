"""Conservative extraction of clearly labelled solar-system measurements."""
import re


def extract_equipment_updates(message: str) -> dict:
    """Extract unambiguous measurements without guessing missing information."""
    updates = {}
    text = message.lower()

    patterns = {
        "battery_soc_percent": [
            r"\b(?:battery\s+)?soc\s*(?:is|:|=|at)?\s*(\d+(?:\.\d+)?)\s*%",
            r"\bbattery\s+(?:is\s+)?(?:at\s+)?(\d+(?:\.\d+)?)\s*%",
        ],
        "pv_voltage_v": [
            r"\bpv\s+voltage\s*(?:is|:|=|at)?\s*(\d+(?:\.\d+)?)\s*v\b",
        ],
        "pv_power_w": [
            r"\b(?:pv|solar|charging)\s+power\s*(?:is|:|=|at|remains\s+at)?\s*(\d+(?:\.\d+)?)\s*w\b",
        ],
    }

    for field, expressions in patterns.items():
        for expression in expressions:
            match = re.search(expression, text)
            if match:
                value = float(match.group(1))
                if field == "battery_soc_percent" and not 0 <= value <= 100:
                    continue
                updates[field] = value
                break

    return updates
