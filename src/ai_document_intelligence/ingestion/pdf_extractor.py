"""Extract text from PDF documents while preserving page metadata."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf


class PDFExtractionError(Exception):
    """Base exception for PDF extraction failures."""


class InvalidPDFError(PDFExtractionError):
    """Raised when a file cannot be opened as a valid PDF."""


class PDFPasswordRequiredError(PDFExtractionError):
    """Raised when a PDF requires a password."""


class PDFNoExtractableTextError(PDFExtractionError):
    """Raised when a PDF contains no extractable text."""


@dataclass(frozen=True)
class ExtractedPage:
    """Text extracted from one PDF page."""

    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    """Text extracted from a PDF document."""

    document_id: str
    source_name: str
    pages: list[ExtractedPage]
    page_count: int


def extract_pdf(path: Path, document_id: str) -> ExtractedDocument:
    """Extract non-empty text from a PDF, retaining one-based page numbers."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        document = pymupdf.open(path)
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise InvalidPDFError(f"Unable to open PDF: {path}") from exc

    with document:
        if document.needs_pass:
            raise PDFPasswordRequiredError(f"PDF requires a password: {path.name}")

        extracted_pages = [
            ExtractedPage(
                page_number=page_number,
                text=page.get_text().strip(),
            )
            for page_number, page in enumerate(document, start=1)
        ]

    if not any(page.text for page in extracted_pages):
        raise PDFNoExtractableTextError(
            f"No extractable text found in PDF: {path.name}"
        )

    return ExtractedDocument(
        document_id=document_id,
        source_name=path.name,
        pages=extracted_pages,
        page_count=len(extracted_pages),
    )
