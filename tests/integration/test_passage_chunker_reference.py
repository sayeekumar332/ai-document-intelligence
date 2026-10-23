"""Integration validation of passage chunking on the reference patent."""

import os
from pathlib import Path

import pytest

from ai_document_intelligence.ingestion.passage_chunker import chunk_document
from ai_document_intelligence.ingestion.pdf_extractor import extract_pdf


def test_reference_patent_passages_preserve_provenance() -> None:
    """Verify passage limits, metadata, and stable IDs on a real PDF."""
    configured_path = os.environ.get("REFERENCE_PDF_PATH")

    if not configured_path:
        pytest.skip("Set REFERENCE_PDF_PATH to run the real-PDF integration test.")

    pdf_path = Path(configured_path).expanduser()

    if not pdf_path.is_file():
        pytest.skip(f"Reference PDF is unavailable: {pdf_path}")

    document = extract_pdf(pdf_path, document_id="us4803615-reference")

    first_run = chunk_document(document)
    second_run = chunk_document(document)

    assert first_run
    assert len(first_run) == len(second_run)
    assert [p.passage_id for p in first_run] == [p.passage_id for p in second_run]

    passage_ids = [passage.passage_id for passage in first_run]
    assert len(passage_ids) == len(set(passage_ids))

    for passage in first_run:
        assert 0 < len(passage.text) <= 800
        assert passage.text.strip()
        assert passage.document_id == document.document_id
        assert passage.source_name == pdf_path.name
        assert 1 <= passage.page_number <= document.page_count

    # Every page containing extractable text must have at least one passage.
    source_pages_with_text = {
        page.page_number for page in document.pages if page.text.strip()
    }
    passage_pages = {passage.page_number for passage in first_run}
    assert source_pages_with_text <= passage_pages

    # Passages must remain ordered by source page and passage index.
    positions = [
        (
            passage.page_number,
            int(passage.passage_id.rsplit(":c", 1)[1]),
        )
        for passage in first_run
    ]
    assert positions == sorted(positions)
