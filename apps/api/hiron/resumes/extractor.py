"""Resume text extraction module supporting PDF, DOCX, and TXT files per Engineering Guidelines §6."""

import io

import docx
import pdfplumber
import structlog

from hiron.resumes.exceptions import ResumeParseFailedError

logger = structlog.get_logger("hiron.resumes.extractor")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF file bytes using pdfplumber."""
    try:
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.debug("Empty or scanned page in PDF", page=page_idx)

        extracted = "\n\n".join(text_parts).strip()
        if not extracted:
            raise ResumeParseFailedError(
                "Unable to extract text from PDF (file may be empty, scanned, or encrypted)"
            )
        return extracted
    except Exception as exc:
        if isinstance(exc, ResumeParseFailedError):
            raise
        logger.warning("PDF text extraction failed", error=str(exc))
        raise ResumeParseFailedError(f"PDF extraction failed: {exc}") from exc


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from DOCX file bytes using python-docx."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        text_parts: list[str] = []
        for paragraph in doc.paragraphs:
            if paragraph.text and paragraph.text.strip():
                text_parts.append(paragraph.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text_parts.append(row_text)

        extracted = "\n".join(text_parts).strip()
        if not extracted:
            raise ResumeParseFailedError(
                "Unable to extract text from DOCX (document appears empty)"
            )
        return extracted
    except Exception as exc:
        if isinstance(exc, ResumeParseFailedError):
            raise
        logger.warning("DOCX text extraction failed", error=str(exc))
        raise ResumeParseFailedError(f"DOCX extraction failed: {exc}") from exc


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from plain text file bytes with encoding fallback."""
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1").strip()
        except Exception as exc:
            raise ResumeParseFailedError(f"TXT decoding failed: {exc}") from exc


def extract_text_from_file(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Dispatch text extraction based on MIME type or filename extension."""
    if not file_bytes:
        raise ResumeParseFailedError("File content is empty (0 bytes)")

    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    if content_type == "application/pdf" or ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    if (
        content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or ext == ".docx"
    ):
        return extract_text_from_docx(file_bytes)
    if content_type == "text/plain" or ext == ".txt":
        return extract_text_from_txt(file_bytes)

    raise ResumeParseFailedError(
        f"Unsupported content type '{content_type}' or extension '{ext}' for text extraction"
    )
