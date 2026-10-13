
import json
import re
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[1] / "knowledge_base" / "default"

GUIDES = {
    "battery": (
        "KB-BATTERY",
        "Battery checks",
        "Check charging availability, state of charge and recorded voltage against the specific manufacturer's manual."
    ),
    "inverter": (
        "KB-INVERTER",
        "Inverter fault checks",
        "Record the make, model and error code; consult the matching manual. Do not open energized equipment."
    ),
    "solar": (
        "KB-PV",
        "Solar generation checks",
        "Compare production with sunlight, shading and historic trends. Do not touch energized PV wiring."
    ),
    "temperature": (
        "KB-THERMAL",
        "Overheating checks",
        "Check accessible ventilation and arrange qualified inspection for overheating."
    ),
}


def load_records(filename):
    path = KB_DIR / filename

    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("records", [])


def retrieve(question):
    q = question.lower()
    results = []

    code_records = load_records("faults_and_warnings.json")
    troubleshooting = load_records("troubleshooting.json")
    general = load_records("knowledge_records.json")

    # Explicit code lookup: "fault 14", "warning 61", etc.
    match = re.search(
        r"\b(fault|error|warning|alarm)\s*(?:code\s*)?0*(\d{1,2})\b",
        q
    )

    if match:
        requested_type = match.group(1)
        code = match.group(2).zfill(2)

        for record in code_records:
            if record["code"] != code:
                continue

            event_type = record["event_type"]

            # Keep fault and warning categories distinct.
            if requested_type in ("fault", "error") and event_type != "fault":
                continue

            if requested_type in ("warning", "alarm") and event_type != "warning":
                continue

            results.append({
                "id": record["id"],
                "title": f"{event_type.title()} code {code}",
                "text": (
                    f"{record['meaning']}. "
                    "This meaning is documented for the source "
                    "manual's inverter family only."
                ),
                "source_id": record["source_id"],
                "source_page": record["source_pdf_page"]
            })

            if event_type == "fault":
                for item in troubleshooting:
                    if code in item.get("fault_codes", []):
                        results.append({
                            "id": item["id"],
                            "title": item["symptom"],
                            "text": (
                                "Possible cause: "
                                + item["possible_cause"]
                                + ". Manual guidance: "
                                + "; ".join(item["manual_guidance"])
                            ),
                            "source_id": item["source_id"],
                            "source_page": item["source_pdf_page"]
                        })

        if results:
            return results[:3]

    # General topic matching against knowledge records.
    for record in general:
        title = record.get("title", "")
        topic = record.get("topic", "")
        content = record.get("content", "")

        keywords = set(
            re.findall(r"[a-z]{4,}", title.lower() + " " + topic.lower())
        )

        if any(word in q for word in keywords):
            results.append({
                "id": record["id"],
                "title": title,
                "text": content,
                "source_id": record.get("source_id"),
                "source_section": record.get("source_section")
            })

    # Retain the original generic fallback guides.
    for keyword, guide in GUIDES.items():
        if keyword in q:
            results.append({
                "id": guide[0],
                "title": guide[1],
                "text": guide[2]
            })

    return results[:3]
