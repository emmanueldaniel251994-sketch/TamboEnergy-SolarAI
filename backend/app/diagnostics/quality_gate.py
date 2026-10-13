"""Conservative post-diagnosis validation; no manufacturer facts are invented."""
from pydantic import BaseModel, Field
from .engine import DiagnosticRequest, DiagnosticResult, _category, diagnose

class QualityReview(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    disposition: str
    result: DiagnosticResult

CHARGING_TERMS = ('charging', 'charge', 'mppt', 'pv', 'battery', 'bms', 'solar', 'panel')
AC_TERMS = ('generator', 'grid', 'ac input', 'frequency', 'waveform', 'utility')
HAZARDOUS = ('bypass protection', 'bridge terminals', 'open energized', 'live electrical test', 'disable bms')

def review(req: DiagnosticRequest, result: DiagnosticResult) -> QualityReview:
    """Fail closed for obvious relevance, provenance and safety violations.

    This is a rule-based safety net, not a guarantee of technical correctness.
    """
    issues: list[str] = []
    category = _category(req.question, req.profile)
    evidence = ' '.join(result.possible_causes + result.recommended_checks + result.suggested_solutions).lower()
    if category == 'pv':
        if not any(term in evidence for term in CHARGING_TERMS):
            issues.append('Charging complaint lacks relevant PV/battery guidance')
        if any(term in evidence for term in AC_TERMS) and not any(term in evidence for term in CHARGING_TERMS):
            issues.append('Charging complaint redirected to AC input')
    if result.sources:
        for source in result.sources:
            if not isinstance(source, dict) or not source.get('source_id'):
                issues.append('Source entry lacks verifiable source_id')
                break
    if result.suggested_solutions and any(term in ' '.join(result.suggested_solutions).lower() for term in HAZARDOUS):
        issues.append('Potentially hazardous corrective action')
    if req.profile.industrial_risk and result.safety_level != 'industrial_specialist':
        issues.append('Industrial system lacks specialist escalation')
    if issues:
        safe = diagnose(req)
        # If baseline itself is unsafe or irrelevant, fail closed with no action instructions.
        safe.suggested_solutions = []
        safe.status = 'manual_review_required'
        safe.confidence = 'low'
        safe.summary = ('Diagnostic response withheld by quality review. ' 
                        'Additional verified equipment evidence and qualified review are required.')
        safe.sources = []
        return QualityReview(passed=False, issues=issues, disposition='withheld', result=safe)
    return QualityReview(passed=True, disposition='accepted', result=result)

def diagnose_checked(req: DiagnosticRequest) -> QualityReview:
    return review(req, diagnose(req))
