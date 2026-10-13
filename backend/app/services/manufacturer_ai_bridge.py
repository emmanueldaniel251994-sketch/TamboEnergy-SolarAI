"""Phase 3E bridge: verified manufacturer evidence for the existing AI endpoint.

Never sends manufacturer record text to an LLM; output is deterministic and sourced.
"""
from app.services.manufacturer_chat import answer_manufacturer_question


def enrich_ai_response(db, question, diagnostic, equipment_model_id=None, fault_code=None):
    """Return manufacturer-grounded response or None for legacy assistant behavior."""
    if equipment_model_id is None and fault_code is None:
        return None
    if equipment_model_id is None or fault_code is None:
        raise ValueError("equipment_model_id and fault_code must be provided together")
    result = answer_manufacturer_question(db, question, equipment_model_id, fault_code)
    if result is None:
        return None
    response = {
        "mode": result["mode"],
        "answer": result["answer"],
        "sources": result["sources"],
        "grounded": result["grounded"],
        "equipment_model_id": equipment_model_id,
        "fault_code": result["fault_code"],
        "safety_notice": result["safety_notice"],
    }
    # Preserve existing telemetry-derived diagnostic without asserting it is
    # verified manufacturer guidance.
    if diagnostic is not None:
        response["telemetry_diagnostic"] = diagnostic
    return response
