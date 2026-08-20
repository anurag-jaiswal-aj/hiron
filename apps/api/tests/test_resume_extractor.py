"""Unit tests for resume text extraction from TXT, PDF, and DOCX files."""

import pytest
from apps.worker.src.extractor import (
    extract_text_from_docx,
    extract_text_from_file,
    extract_text_from_pdf,
    extract_text_from_txt,
)

from hiron.resumes.exceptions import ResumeParseFailedError


def test_extract_text_from_txt_success() -> None:
    """Verify plain text extraction from UTF-8 and latin-1 encoded bytes."""
    sample_text = "John Doe\nSoftware Engineer\nPython, FastAPI, Docker"
    utf8_bytes = sample_text.encode("utf-8")

    extracted = extract_text_from_txt(utf8_bytes)
    assert "John Doe" in extracted
    assert "Software Engineer" in extracted

    latin1_bytes = sample_text.encode("latin-1")
    extracted_latin = extract_text_from_txt(latin1_bytes)
    assert "Python" in extracted_latin


def test_extract_text_from_empty_file_raises_error() -> None:
    """Verify 0-byte file content raises ResumeParseFailedError."""
    with pytest.raises(ResumeParseFailedError):
        extract_text_from_file(b"", "text/plain", "empty.txt")


def test_extract_text_unsupported_content_type_raises_error() -> None:
    """Verify unsupported content type raises ResumeParseFailedError."""
    with pytest.raises(ResumeParseFailedError):
        extract_text_from_file(b"some content", "image/png", "photo.png")


def test_extract_text_from_pdf_corrupted_raises_error() -> None:
    """Verify corrupted PDF bytes raise ResumeParseFailedError."""
    corrupted_pdf_bytes = b"%PDF-1.4 invalid pdf structure content..."
    with pytest.raises(ResumeParseFailedError):
        extract_text_from_pdf(corrupted_pdf_bytes)


def test_extract_text_from_docx_corrupted_raises_error() -> None:
    """Verify corrupted DOCX bytes raise ResumeParseFailedError."""
    corrupted_docx_bytes = b"PK\x03\x04 invalid docx zip content..."
    with pytest.raises(ResumeParseFailedError):
        extract_text_from_docx(corrupted_docx_bytes)
