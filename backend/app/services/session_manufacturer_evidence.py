"""Exact-model evidence alongside general guidance, without injecting corrective actions."""
from datetime import datetime, timezone
from app.diagnostics.conversation import ConversationResponse
from app.diagnostics.engine import _category
from app.diagnostics.quality_gate import HAZARDOUS
from app.models.manufacturer_knowledge import Manufacturer, EquipmentModel
from app.services.manufacturer_grounding import grounded_diagnostic


def evidence(db, response, question):
    profile = response.profile
    if not profile.equipment_model_id or not profile.fault_code or not profile.fault_code.strip():
        return None
    base = {'equipment_model_id': profile.equipment_model_id, 'fault_code': profile.fault_code.strip(),
            'grounded': False, 'matches': [], 'sources': [],
            'checked_at': datetime.now(timezone.utc).isoformat()}
    if not response.quality_review_passed or profile.industrial_risk or _category(question, profile) == 'emergency':
        return {**base, 'status': 'withheld', 'message': 'Model-specific evidence requires qualified review; general safety escalation remains in force.'}
    model = db.get(EquipmentModel, profile.equipment_model_id)
    if model is None:
        return {**base, 'status': 'no_verified_match', 'message': 'The selected equipment model is no longer available.'}
    maker = db.get(Manufacturer, model.manufacturer_id)
    kind = model.equipment_type.casefold()
    prefix = 'inverter' if 'inverter' in kind else 'battery' if 'battery' in kind else 'panel' if 'panel' in kind else None
    if prefix:
        reported_model = getattr(profile, f'{prefix}_model')
        reported_brand = getattr(profile, f'{prefix}_brand')
        def known(value):
            return value and value.strip().casefold() not in {'', 'unknown', 'not known', 'n/a'}
        if ((known(reported_model) and reported_model.strip().casefold() != model.model_name.strip().casefold())
                or (known(reported_brand) and (maker is None or reported_brand.strip().casefold() != maker.name.strip().casefold()))):
            return {**base, 'status': 'model_mismatch', 'message': 'The selected registry model conflicts with the reported equipment details. Confirm the exact manufacturer and model.'}
    result = grounded_diagnostic(db, profile.equipment_model_id, profile.fault_code.strip())
    if not result or not result['grounded']:
        return {**base, 'status': 'no_verified_match', 'message': 'No fully verified manufacturer record matches this exact model and code.'}
    # Even approved registry content is not allowed to bypass the diagnostic gate.
    content = ' '.join(str(item.get(key) or '') for item in result['matches'] for key in ('description', 'recommended_action')).casefold()
    if any(term in content for term in HAZARDOUS):
        return {**base, 'status': 'withheld', 'message': 'Manufacturer evidence was withheld pending qualified safety review.'}
    matches = [{'fault_code': item['fault_code'], 'description': item['description'][:1000],
                'description_truncated': len(item['description']) > 1000, 'severity': item['severity'],
                'source_document_id': item['source_document_id']} for item in result['matches'][:5]]
    doc_ids = {item['source_document_id'] for item in matches}
    return {**base, 'status': 'verified', 'grounded': True, 'model_name': result['model_name'],
            'manufacturer_name': result['manufacturer_name'], 'matches': matches,
            'sources': [source for source in result['sources'] if source['document_id'] in doc_ids][:5],
            'message': 'Verified exact-model fault records. These are evidence excerpts, not instructions to operate or repair equipment.',
            'safety_notice': result['safety_notice']}


def attach_evidence(db, response, question):
    return response.model_copy(update={'manufacturer_evidence': evidence(db, response, question)})


def refresh_stored_evidence(db, metadata, cache):
    """Revalidate citations on reads without changing stored messages or evidence snapshots."""
    if not isinstance(metadata, dict) or not isinstance(metadata.get('manufacturer_evidence'), dict):
        return metadata
    # Never turn originally withheld material into guidance during history retrieval.
    if metadata['manufacturer_evidence'].get('status') == 'withheld':
        return metadata
    try:
        response = ConversationResponse.model_validate(metadata)
    except ValueError:
        return {**metadata, 'manufacturer_evidence': {'status': 'withheld', 'grounded': False,
            'message': 'Stored evidence cannot be safely revalidated.', 'matches': [], 'sources': []}}
    profile = response.profile
    key = (profile.equipment_model_id, profile.fault_code, response.quality_review_passed,
           profile.industrial_risk, _category('', profile),
           profile.inverter_brand, profile.inverter_model, profile.battery_brand,
           profile.battery_model, profile.panel_brand, profile.panel_model)
    if key not in cache:
        cache[key] = evidence(db, response, '')
    return {**metadata, 'manufacturer_evidence': cache[key]}
