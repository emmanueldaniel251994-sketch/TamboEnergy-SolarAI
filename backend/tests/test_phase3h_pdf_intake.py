"""Eight isolated tests using synthetic PDFs only."""
import hashlib
import io
import pytest
from pypdf import PdfWriter
from app.services.manufacturer_pdf_intake import (
    PdfIntakeError, inspect_pdf, save_pending_pdf, MAX_PDF_BYTES,
)

def pdf():
    out = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(out)
    return out.getvalue()

def test_pdf_header_and_pages():
    result = inspect_pdf(pdf())
    assert result['pages'] == 1
    assert result['verification_status'] == 'pending'

def test_sha256_matches():
    data = pdf()
    assert inspect_pdf(data)['sha256'] == hashlib.sha256(data).hexdigest()

def test_empty_rejected():
    with pytest.raises(PdfIntakeError): inspect_pdf(b'')

def test_non_pdf_rejected():
    with pytest.raises(PdfIntakeError): inspect_pdf(b'not a PDF')

def test_oversized_rejected():
    with pytest.raises(PdfIntakeError): inspect_pdf(b'%PDF-' + b'x' * MAX_PDF_BYTES)

def test_malformed_pdf_rejected():
    with pytest.raises(PdfIntakeError): inspect_pdf(b'%PDF-1.7\ninvalid')

def test_save_pending_metadata(tmp_path):
    data = pdf()
    result = save_pending_pdf(data, inspect_pdf(data), 3, 'Test Manual',
                              'https://example.org/manual.pdf', str(tmp_path))
    assert result['verification_status'] == 'pending'
    assert (tmp_path / (result['sha256'] + '.pdf')).read_bytes() == data

def test_duplicate_not_overwritten(tmp_path):
    data = pdf()
    report = inspect_pdf(data)
    save_pending_pdf(data, report, 3, 'Test', 'https://example.org/doc', str(tmp_path))
    with pytest.raises(PdfIntakeError):
        save_pending_pdf(data, report, 3, 'Test', 'https://example.org/doc', str(tmp_path))
