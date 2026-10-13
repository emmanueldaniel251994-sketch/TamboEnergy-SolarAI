"""Preview-first metadata intake. Never downloads URLs or verifies documents."""
import csv
import io
import json
from urllib.parse import urlsplit
from sqlalchemy.orm import Session
from app.models.manufacturer_knowledge import EquipmentModel, TechnicalDocument

MAX_BYTES = 512_000
MAX_ROWS = 300
FIELDS = {"equipment_model_id", "title", "document_type", "source_url", "document_version"}
REQUIRED = {"equipment_model_id", "title", "document_type", "source_url"}

def parse_manifest(raw: bytes, fmt: str):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Manifest must be nonempty and at most 512 KB")
    try:
        content = raw.decode("utf-8-sig")
        if fmt == "csv":
            reader = csv.DictReader(io.StringIO(content))
            if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not REQUIRED.issubset(reader.fieldnames) or not set(reader.fieldnames).issubset(FIELDS):
                raise ValueError("Invalid CSV columns")
            rows = list(reader)
        elif fmt == "json":
            rows = json.loads(content)
        else:
            raise ValueError("Use csv or json")
    except (UnicodeError, json.JSONDecodeError, csv.Error) as exc:
        raise ValueError("Malformed manifest") from exc
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Expected an array of up to 300 objects")
    return rows

def valid_source_url(value: str):
    try:
        u = urlsplit(value)
        return (u.scheme == "https" and bool(u.hostname) and not u.username and not u.password
                and not u.fragment and len(value) <= 2048 and not any(ch.isspace() for ch in value)
                and u.port in (None, 443))
    except ValueError:
        return False

def prepare_manifest(db: Session, rows):
    accepted, rejected, skipped = [], [], []
    seen = set()
    for line, row in enumerate(rows, 1):
        try:
            if set(row) - FIELDS or not REQUIRED.issubset(row):
                raise ValueError("Unexpected or missing fields")
            model_id = int(row["equipment_model_id"])
            title = str(row["title"]).strip()
            kind = str(row["document_type"]).strip()
            url = str(row["source_url"]).strip()
            version = str(row.get("document_version") or "").strip()
            if model_id < 1 or not db.get(EquipmentModel, model_id):
                raise ValueError("Unknown equipment model")
            if not title or len(title) > 250 or not kind or len(kind) > 80 or len(version) > 100:
                raise ValueError("Invalid document metadata")
            if not valid_source_url(url):
                raise ValueError("Source must be a valid HTTPS URL")
            key = (model_id, url)
            if key in seen:
                skipped.append({"row": line, "reason": "Duplicate source in batch"})
                continue
            seen.add(key)
            existing = db.query(TechnicalDocument).filter_by(equipment_model_id=model_id, source_url=url).first()
            if existing:
                skipped.append({"row": line, "reason": "Source already registered; no overwrite"})
                continue
            accepted.append({"row": line, "equipment_model_id": model_id, "title": title,
                             "document_type": kind, "source_url": url, "document_version": version or None})
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"row": line, "reason": str(exc)[:160]})
    return {"accepted": accepted, "rejected": rejected, "skipped": skipped}

def commit_pending_documents(db: Session, report):
    if report["rejected"]:
        raise ValueError("Rejected rows present; nothing committed")
    try:
        for row in report["accepted"]:
            db.add(TechnicalDocument(**{k: v for k, v in row.items() if k != "row"},
                                     verification_status="pending"))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(report["accepted"])
