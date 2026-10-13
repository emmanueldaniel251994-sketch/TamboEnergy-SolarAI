"""Regression checks: every conversational diagnosis must use reviewed output."""
from types import SimpleNamespace

from app.diagnostics import conversation as conversation_module


def _result(status='needs_information'):
    return SimpleNamespace(
        summary='Reviewed diagnostic summary',
        status=status,
        follow_up_questions=['What is the battery SOC?'],
        possible_causes=['BMS charge inhibition'],
        recommended_checks=['Read BMS status on the monitoring display'],
        suggested_solutions=['Consult the manufacturer guidance'],
        sources=[],
        safety_notice='Qualified personnel only',
        safety_level='qualified_technician',
    )


def test_conversation_uses_quality_gate(monkeypatch):
    seen = []
    def fake_checked(req):
        seen.append(req)
        return SimpleNamespace(passed=True, result=_result())
    monkeypatch.setattr(conversation_module, 'diagnose_checked', fake_checked)
    response = conversation_module.converse(conversation_module.ConversationRequest(
        question='My battery is not charging despite sunlight',
    ))
    assert len(seen) == 1
    assert response.status == 'needs_information'
    assert response.suggested_solutions == ['Consult the manufacturer guidance']
    assert 'Next question:' in response.message


def test_conversation_withholds_unapproved_guidance(monkeypatch):
    monkeypatch.setattr(conversation_module, 'diagnose_checked', lambda req:
        SimpleNamespace(passed=False, result=_result('manual_review_required')))
    response = conversation_module.converse(conversation_module.ConversationRequest(
        question='My solar inverter is not charging',
    ))
    assert response.status == 'manual_review_required'
    assert response.suggested_solutions == []
    assert response.recommended_checks == []
    assert response.possible_causes == []
    assert response.next_questions == []
    assert 'Next question:' not in response.message


def test_conversation_rejects_unknown_updates():
    import pytest
    with pytest.raises(ValueError, match='Unknown profile fields'):
        conversation_module.converse(conversation_module.ConversationRequest(
            question='My battery is not charging', updates={'not_a_real_field': 1},
        ))
