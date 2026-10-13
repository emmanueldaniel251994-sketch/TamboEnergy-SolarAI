"""Phase 3E bridge tests: no external LLM, network or production database."""
from unittest.mock import patch
import pytest
from app.services.manufacturer_ai_bridge import enrich_ai_response


def test_legacy_request_is_unchanged():
    assert enrich_ai_response(None, "How is my inverter?", None) is None


def test_partial_model_rejected():
    with pytest.raises(ValueError):
        enrich_ai_response(None, "What does code mean?", None, equipment_model_id=1)


def test_partial_fault_rejected():
    with pytest.raises(ValueError):
        enrich_ai_response(None, "What does code mean?", None, fault_code="61")


def test_unknown_model_not_fabricated():
    with patch("app.services.manufacturer_ai_bridge.answer_manufacturer_question", return_value=None):
        assert enrich_ai_response(None, "Explain code 61", None, 999, "61") is None


def test_verified_response_keeps_sources_and_telemetry():
    record = {"mode": "verified_manufacturer_knowledge", "answer": "Confirmed record",
              "sources": [{"title": "Manual", "source_url": "https://example.org/manual"}],
              "grounded": True, "fault_code": "61", "safety_notice": "Be safe"}
    diagnosis = {"title": "Telemetry alert"}
    with patch("app.services.manufacturer_ai_bridge.answer_manufacturer_question", return_value=record):
        result = enrich_ai_response(None, "Explain code 61", diagnosis, 7, "61")
    assert result["sources"] == record["sources"]
    assert result["telemetry_diagnostic"] is diagnosis
    assert result["grounded"] is True


def test_unverified_result_remains_unverified():
    record = {"mode": "no_verified_match", "answer": "No verified match", "sources": [],
              "grounded": False, "fault_code": "61", "safety_notice": "Be safe"}
    with patch("app.services.manufacturer_ai_bridge.answer_manufacturer_question", return_value=record):
        result = enrich_ai_response(None, "Explain code 61", None, 7, "61")
    assert result["grounded"] is False
    assert result["sources"] == []
