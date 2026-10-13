"""Standalone parser process. It receives PDF bytes on stdin, never storage paths."""
import io
import json
import sys

MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PAGES = 80
MAX_TEXT_CHARS = 100_000
MEMORY_BYTES = 256 * 1024 * 1024
OUTPUT_BYTES = 800_000


def resource_limits():
    try:
        import resource
    except ImportError:
        # Development on Windows retains the parent timeout and output bounds.
        if '--require-limits' in sys.argv:
            raise ValueError('PDF resource limits are unavailable')
        return
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES, OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))


def parse():
    resource_limits()
    # Import only after installing resource limits.
    from pypdf import PdfReader
    data = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
    if not data or len(data) > MAX_PDF_BYTES or not data.startswith(b'%PDF-'):
        raise ValueError('Invalid PDF input')
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported')
    pages = len(reader.pages)
    if pages < 1 or pages > MAX_PAGES:
        raise ValueError('PDF must have 1 to 80 pages')
    parts, count = [], 0
    for page in reader.pages:
        remaining = MAX_TEXT_CHARS - count
        if remaining <= 0:
            break
        text = (page.extract_text() or '')[:remaining]
        parts.append(text)
        count += len(text)
    return {'pages': pages, 'extracted_chars': count, 'text': '\n\n'.join(parts),
            'truncated': count >= MAX_TEXT_CHARS}


if __name__ == '__main__':
    try:
        result = {'result': parse()}
    except Exception:
        # Do not disclose parser paths, document text, or exception details.
        result = {'error': 'PDF parsing failed or exceeded resource limits'}
    sys.stdout.write(json.dumps(result, ensure_ascii=True))
