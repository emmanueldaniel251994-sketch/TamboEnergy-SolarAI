"""Parser/validation tests without external database or network."""
import json
import pytest
from unittest.mock import Mock
from app.services.manufacturer_document_intake import parse_manifest, prepare_manifest, valid_source_url, commit_pending_documents

def sample():
    return {"equipment_model_id": 1, "title": "Manual", "document_type": "manual",
            "source_url": "https://manufacturer.example/manual.pdf"}

def db_mock(existing=None, model=True):
    db = Mock()
    db.get.return_value = object() if model else None
    db.query.return_value.filter_by.return_value.first.return_value = existing
    return db

def test_parse_json():
    assert parse_manifest(json.dumps([sample()]).encode(), "json")[0]["title"] == "Manual"

def test_parse_csv():
    data = b"equipment_model_id,title,document_type,source_url\n1,Manual,manual,https://manufacturer.example/manual.pdf\n"
    assert len(parse_manifest(data, "csv")) == 1

def test_reject_non_https():
    assert not valid_source_url("http://manufacturer.example/manual.pdf")
    assert not valid_source_url("https://user:pass@manufacturer.example/doc")
    assert not valid_source_url("https://manufacturer.example:444/doc")

def test_reject_invalid_json():
    with pytest.raises(ValueError):
        parse_manifest(b"{oops", "json")

def test_pending_accepted():
    report = prepare_manifest(db_mock(), [sample()])
    assert len(report["accepted"]) == 1
    assert not report["rejected"]

def test_duplicate_in_batch_skipped():
    report = prepare_manifest(db_mock(), [sample(), sample()])
    assert len(report["accepted"]) == 1
    assert len(report["skipped"]) == 1

def test_unknown_model_rejected():
    assert len(prepare_manifest(db_mock(model=False), [sample()])["rejected"]) == 1

def test_commit_pending_and_reject_errors():
    db = db_mock()
    report = prepare_manifest(db, [sample()])
    assert commit_pending_documents(db, report) == 1
    assert db.add.call_args.args[0].verification_status == "pending"
    with pytest.raises(ValueError):
        commit_pending_documents(db, {"accepted": [], "rejected": [{"row": 1}]})
