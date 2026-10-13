"""Client-carried diagnostic context with quality-reviewed, non-redundant follow-ups."""
from typing import Any
from pydantic import BaseModel, Field
from .equipment_profile import EquipmentProfile
from .engine import DiagnosticRequest
from .quality_gate import diagnose_checked


class ConversationRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    profile: EquipmentProfile = Field(default_factory=EquipmentProfile)
    updates: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    message: str
    status: str
    profile: EquipmentProfile
    next_questions: list[str]
    possible_causes: list[str]
    recommended_checks: list[str]
    suggested_solutions: list[str]
    sources: list[dict]
    safety_notice: str
    safety_level: str


def _known(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or value.strip().lower() not in ('', 'unknown', 'not known', 'n/a'))


def _refine_questions(questions: list[str], profile: EquipmentProfile) -> list[str]:
    """Refine recognized multi-part questions; do not infer equipment facts from prose."""
    refined = []
    data = profile.model_dump()
    for question in questions:
        lower = question.lower()
        # Only rewrite the known, explicit multi-part question, avoiding broad keyword
        # suppression that could remove useful battery or PV troubleshooting questions.
        if ('battery chemistry' in lower and 'manufacturer' in lower and 'model' in lower):
            missing = []
            if not _known(data.get('battery_technology')):
                missing.append('chemistry')
            if not _known(data.get('battery_brand')):
                missing.append('manufacturer')
            if not _known(data.get('battery_model')):
                missing.append('exact model')
            if not missing:
                continue
            if len(missing) == 1:
                question = 'What is the battery ' + missing[0] + '?'
            elif len(missing) == 2:
                question = 'What are the battery ' + ' and '.join(missing) + '?'
            else:
                question = 'What are the battery chemistry, manufacturer and exact model?'
        # If the engine requests a specific measurement already provided, skip it;
        # do not skip questions about *other* measurements in the same subsystem.
        elif ('state of charge' in lower or '(soc)' in lower) and _known(data.get('battery_soc_percent')):
            continue
        elif ('pv input voltage' in lower or 'pv voltage' in lower) and _known(data.get('pv_voltage_v')) and 'power' not in lower:
            continue
        elif ('pv charging power' in lower or 'pv power' in lower) and _known(data.get('pv_power_w')) and 'voltage' not in lower:
            continue
        if question not in refined:
            refined.append(question)
    return refined


def converse(request: ConversationRequest) -> ConversationResponse:
    current = request.profile.model_dump()
    allowed = set(EquipmentProfile.model_fields)
    unknown = set(request.updates) - allowed
    if unknown:
        raise ValueError('Unknown profile fields: ' + ', '.join(sorted(unknown)))
    for field, value in request.updates.items():
        if value is not None:
            current[field] = value
    profile = EquipmentProfile.model_validate(current)
    review = diagnose_checked(DiagnosticRequest(question=request.question, profile=profile))
    result = review.result
    # Fail closed: a rejected review must never leak diagnostic guidance.
    approved = bool(review.passed)
    questions = _refine_questions(result.follow_up_questions, profile) if approved else []
    summary = result.summary
    if questions:
        summary += '\n\nNext question: ' + questions[0]
    elif result.possible_causes and approved:
        summary += '\n\nPossible causes: ' + '; '.join(result.possible_causes)
    return ConversationResponse(
        message=summary, status=result.status, profile=profile,
        next_questions=questions,
        possible_causes=result.possible_causes if approved else [],
        recommended_checks=result.recommended_checks if approved else [],
        suggested_solutions=result.suggested_solutions if approved else [],
        sources=result.sources,
        safety_notice=result.safety_notice, safety_level=result.safety_level,
    )
