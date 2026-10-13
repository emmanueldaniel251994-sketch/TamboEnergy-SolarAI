"""Pure parsing tests, plus schema-safe checks without live Neon access."""
import json
import pytest
from app.services.manufacturer_import import parse_import


def test_valid_json():
    assert parse_import(b'[{"fault_code":"F01"}]', 'json')[0]['fault_code'] == 'F01'


def test_valid_csv():
    raw = b'equipment_model_id,source_document_id,fault_code,description\n1,2,F01,Sample\n'
    assert parse_import(raw, 'csv')[0]['fault_code'] == 'F01'


def test_invalid_format():
    with pytest.raises(ValueError):
        parse_import(b'[]', 'xml')


def test_invalid_json():
    with pytest.raises(ValueError):
        parse_import(b'not json', 'json')


def test_reject_nonlist():
    with pytest.raises(ValueError):
        parse_import(b'{}', 'json')


def test_reject_oversize():
    with pytest.raises(ValueError):
        parse_import(b'x' * 512001, 'csv')


def test_reject_too_many_rows():
    with pytest.raises(ValueError):
        parse_import(json.dumps([{}] * 501).encode(), 'json')


def test_reject_nonobject_row():
    with pytest.raises(ValueError):
        parse_import(b'[1]', 'json')
