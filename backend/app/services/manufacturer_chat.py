"""Conservative manufacturer-specific conversational responses, grounded in Phase 3C."""
from app.services.manufacturer_grounding import grounded_diagnostic

def answer_manufacturer_question(db, question: str, equipment_model_id: int, fault_code: str):
    result = grounded_diagnostic(db, equipment_model_id, fault_code)
    if result is None:
        return None
    if not result["grounded"]:
        answer = (
            "I cannot confirm this fault code for the selected equipment model from "
            "currently verified manufacturer records. Please check the exact model "
            "and consult the manufacturer's official documentation."
        )
    else:
        parts = []
        for item in result["matches"]:
            parts.append(
                f"Verified record for code {item['fault_code']}: {item['description']}. "
                f"Severity: {item['severity']}. "
                + (f"Documented action: {item['recommended_action']}." if item["recommended_action"] else
                   "No documented recommended action is available.")
            )
        answer = "\\n".join(parts)
    return {
        "question": question,
        "equipment_model_id": equipment_model_id,
        "fault_code": result["fault_code"],
        "grounded": result["grounded"],
        "mode": "verified_manufacturer_knowledge" if result["grounded"] else "no_verified_match",
        "answer": answer,
        "sources": result["sources"],
        "safety_notice": result["safety_notice"],
    }
