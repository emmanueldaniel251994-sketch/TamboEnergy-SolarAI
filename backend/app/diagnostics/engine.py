"""Conservative, stateless diagnostic intake engine.

Never applies default-manual fault codes to an unverified manufacturer/model.
Does not issue switching, isolation, live measurement or protection-bypass instructions.
"""
import json
import re
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from .equipment_profile import EquipmentProfile

KB_DIR = Path(__file__).resolve().parents[1] / 'knowledge_base' / 'default'
DEFAULT_SOURCE = 'SRC-DEFAULT-001'
SAFETY = ('Do not open energized equipment, bypass protection, or perform live electrical testing. '
          'Electrical work requires an appropriately qualified and authorized professional.')


class DiagnosticRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    profile: EquipmentProfile = Field(default_factory=EquipmentProfile)
    # Caller sends the profile returned in the previous turn; no cross-user server state.


class DiagnosticResult(BaseModel):
    status: Literal['needs_information', 'preliminary_assessment', 'manual_review_required']
    summary: str
    possible_causes: list[str] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    suggested_solutions: list[str] = Field(default_factory=list)
    tools_or_components: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    confidence: Literal['low', 'medium'] = 'low'
    safety_level: Literal['standard', 'qualified_technician', 'industrial_specialist']
    safety_notice: str = SAFETY
    profile: EquipmentProfile


def _load(name: str) -> list[dict]:
    try:
        data = json.loads((KB_DIR / name).read_text(encoding='utf-8'))
        return data.get('records', []) if isinstance(data, dict) else []
    except (OSError, ValueError, TypeError):
        return []


def _match_code(q: str, profile: EquipmentProfile) -> tuple[str, str] | None:
    m = re.search(r'\b(fault|error|warning|alarm)\s*(?:code\s*)?0*(\d{1,3})\b', q.lower())
    if m:
        return ('warning' if m.group(1) in ('warning', 'alarm') else 'fault', m.group(2).zfill(2))
    if profile.fault_code:
        code = profile.fault_code.strip()
        if re.fullmatch(r'\d{1,3}', code):
            return (profile.fault_category, code.zfill(2))
    return None


def _category(question: str, p: EquipmentProfile) -> str:
    """Prefer the actual reported fault over incidental mentions of grid/generator.

    Do not interpret an unknown power source as an AC-input fault.
    """
    q = (question + ' ' + (p.symptoms or '')).lower()
    if any(term in q for term in ('fire', 'smoke', 'sparking', 'burning smell', 'thermal runaway')):
        return 'emergency'

    # A charging complaint mentioning PV is primarily a PV/charging problem,
    # even when the user also mentions grid, generator, or utility power.
    charging = any(term in q for term in (
        'not charging', 'no charging', 'stopped charging', 'won\'t charge',
        'does not charge', 'doesn\'t charge', 'charging power', 'charge current',
        'charge at zero', 'charging at zero', '0w charging',
    ))
    solar = any(re.search(r'\b' + term + r'\b', q) for term in
                ('solar', 'pv', 'panels?', 'mppt', 'sunlight', 'irradiance'))
    if charging and (solar or p.pv_voltage_v is not None or p.pv_power_w is not None):
        return 'pv'
    if charging or any(term in q for term in ('battery', 'bms', 'state of charge')):
        return 'battery'
    if solar:
        return 'pv'
    if any(term in q for term in ('generator', 'waveform', 'grid', 'mains', 'utility', 'ac input')):
        return 'ac_input'
    if any(term in q for term in ('overheat', 'temperature', 'fan', 'hot')):
        return 'thermal'
    if any(term in q for term in ('overload', 'trip', 'breaker', 'output')):
        return 'output'
    return 'unknown'


CHECKS = {
    'pv': [
        'Read PV voltage, PV power and charge current from the monitoring display.',
        'Compare observed PV values with the verified model-specific MPPT limits.',
        'Check whether the display reports an MPPT or PV-input warning.'
    ],
    'battery': [
        'Read battery voltage, state of charge and charging status from the display or BMS.',
        'Check whether the BMS reports a charge-inhibit or communication alarm.',
        'Confirm battery chemistry and manufacturer-approved charging configuration.'
    ],
    'ac_input': [
        'Check the inverter display for AC input voltage, frequency and source status.',
        'Compare the displayed values with the applicable manufacturer specifications.',
        'Record whether the warning occurs on grid, generator or both.'
    ],
    'thermal': [
        'Check externally accessible ventilation openings for obstruction.',
        'Review displayed temperature and fan warnings without opening equipment.'
    ],
    'output': [
        'Review load percentage, fault history and displayed output readings.',
        'Check whether the load exceeds the documented equipment rating.'
    ],
    'unknown': [
        'Record the displayed error text, equipment model and recent operating conditions.'
    ]
}


def diagnose(req: DiagnosticRequest) -> DiagnosticResult:
    p = req.profile
    q = req.question
    category = _category(q, p)
    industrial = p.industrial_risk
    level = 'industrial_specialist' if industrial else 'qualified_technician'
    if category == 'emergency':
        return DiagnosticResult(
            status='manual_review_required',
            summary='Potential electrical or battery emergency. Keep clear and contact site emergency responders and authorized personnel immediately.',
            recommended_checks=['Do not approach or handle damaged, smoking or burning equipment.'],
            safety_level=level, profile=p,
        )

    questions = []
    if not p.inverter_brand or not p.inverter_model:
        questions.append('What is the inverter or PCS manufacturer and exact model from the nameplate?')
    if not p.rated_capacity_kva:
        questions.append('What is the system rated apparent power in kVA?')
    if category in ('pv', 'battery'):
        if not p.battery_technology or not p.battery_brand or not p.battery_model:
            questions.append('What battery chemistry, manufacturer and exact model are installed?')
        if p.pv_voltage_v is None:
            questions.append('What PV input voltage is shown on the inverter or monitoring display?')
        if p.pv_power_w is None:
            questions.append('What PV charging power is shown (in watts)?')
        if p.battery_soc_percent is None:
            questions.append('What battery state of charge (SOC) does the battery or BMS display?')
        questions.append('Does the inverter or BMS show a charge-inhibit warning or error code?')
    if category == 'ac_input' and p.grid_or_generator == 'unknown':
        questions.append('Does the issue occur on utility power, generator power, or both?')
    if industrial:
        if p.phase_configuration == 'unknown':
            questions.append('Is the system single-phase or three-phase?')
        if p.ac_voltage_v is None:
            questions.append('What is the nominal AC voltage and voltage class from the site documentation?')
        questions.append('Is an authorized site electrical engineer or operations team available to review the event logs?')

    result = DiagnosticResult(
        status='needs_information' if questions else 'preliminary_assessment',
        summary='Initial assessment only. Equipment identity and operating measurements determine the next diagnostic steps.',
        recommended_checks=CHECKS.get(category, CHECKS['unknown']).copy(),
        follow_up_questions=questions[:4], safety_level=level, profile=p,
    )
    if category == 'pv':
        result.possible_causes = ['Insufficient usable PV input despite sunlight', 'MPPT operating-range mismatch', 'Charge controller or BMS charge inhibition']
    elif category == 'battery':
        result.possible_causes = ['Battery charge inhibition', 'Charging configuration mismatch', 'Insufficient charging-source power']
    elif category == 'ac_input':
        result.possible_causes = ['Input voltage/frequency outside acceptable limits', 'Poor generator power quality', 'Incorrect input-source configuration']
    elif category == 'thermal':
        result.possible_causes = ['Insufficient cooling airflow', 'High ambient temperature', 'Cooling system fault']
    elif category == 'output':
        result.possible_causes = ['Load demand above equipment capability', 'Protection or output fault']

    # Source-specific code meanings require explicit model validation; do not guess
    # that a generic 5kVA inverter is part of the default manual family.
    code = _match_code(q, p)
    if code:
        kind, value = code
        result.follow_up_questions.insert(0, 'Can you confirm the exact equipment model and provide its fault-code manual or nameplate?')
        result.follow_up_questions = result.follow_up_questions[:4]
        result.summary = f'{kind.title()} code {value} reported. Its meaning is not verified for this equipment model.'
        result.status = 'manual_review_required'
        # The initial default manual covers 2, 4.2 and 6.2kVA but is not a universal code map.
        # A future manufacturer registry may authorize a code match for an exact model.

    if industrial:
        result.recommended_checks = [c for c in result.recommended_checks if 'externally accessible' in c or 'display' in c or 'monitoring' in c or 'Review' in c or 'Record' in c or 'Compare' in c]
        result.suggested_solutions = ['Escalate to the authorized site electrical/SCADA team for model-specific diagnosis and approved maintenance procedures.']
    elif category == 'thermal':
        result.suggested_solutions = ['Restore unobstructed external ventilation if this can be done safely without accessing energized equipment.']
    elif category == 'output':
        result.suggested_solutions = ['Reduce nonessential connected loads using normal user-operated controls, if permitted by the site operating procedure.']

    result.tools_or_components = ['Inverter monitoring display or authorized monitoring application']
    if category == 'battery':
        result.tools_or_components.append('Manufacturer-approved battery/BMS monitoring interface, if available')
    return result
