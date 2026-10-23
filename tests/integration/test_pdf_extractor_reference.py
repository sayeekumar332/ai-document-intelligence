"""Integration validation against the real patent reference PDF."""

import os
from pathlib import Path

import pytest

from ai_document_intelligence.ingestion.pdf_extractor import extract_pdf


def test_reference_patent_text_and_page_provenance() -> None:
    """Verify text extraction and page numbering on the reference patent."""
    configured_path = os.environ.get("REFERENCE_PDF_PATH")

    if not configured_path:
        pytest.skip("Set REFERENCE_PDF_PATH to run the real-PDF integration test.")

    pdf_path = Path(configured_path).expanduser()

    if not pdf_path.is_file():
        pytest.skip(f"Reference PDF is unavailable: {pdf_path}")

    document = extract_pdf(pdf_path, document_id="us4803615-reference")

    assert document.page_count == 14
    assert len(document.pages) == document.page_count
    assert [page.page_number for page in document.pages] == list(
        range(1, document.page_count + 1)
    )
    assert all(page.text.strip() for page in document.pages)

    total_characters = sum(len(page.text) for page in document.pages)
    assert total_characters > 40_000
