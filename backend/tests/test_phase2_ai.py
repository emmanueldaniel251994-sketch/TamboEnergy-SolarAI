from app.services.ai_assistant import explain
def test_fallback(monkeypatch):
    monkeypatch.setenv("SOLARAI_AI_ENABLED","false")
    result=explain("battery undervoltage",{"title":"Low battery","diagnosis":"battery_undervoltage","recommended_action":"Inspect"})
    assert result["mode"]=="fallback"
    assert "Low battery" in result["answer"]
    assert result["sources"]
def test_unknown(monkeypatch):
    monkeypatch.setenv("SOLARAI_AI_ENABLED","false")
    assert "Provide the inverter model" in explain("Unknown mystery fault")["answer"]
