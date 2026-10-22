from pathlib import Path

import pymupdf
import pytest

from ai_document_intelligence.ingestion.pdf_extractor import (
    InvalidPDFError,
    PDFNoExtractableTextError,
    PDFPasswordRequiredError,
    extract_pdf,
)


def create_pdf(path: Path, pages: list[str]) -> None:
    """Create a small PDF fixture for extraction tests."""
    document = pymupdf.open()
    try:
        for page_text in pages:
            page = document.new_page()
            page.insert_text((72, 72), page_text)
        document.save(path)
    finally:
        document.close()


def test_extract_single_page_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "single.pdf"
    create_pdf(pdf_path, ["Embedded systems are practical."])

    result = extract_pdf(pdf_path, document_id="doc-001")

    assert result.document_id == "doc-001"
    assert result.source_name == "single.pdf"
    assert result.page_count == 1
    assert result.pages[0].page_number == 1
    assert "Embedded systems are practical." in result.pages[0].text


def test_extract_multiple_pages_preserves_page_numbers(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "multiple.pdf"
    create_pdf(pdf_path, ["First page content.", "Second page content."])

    result = extract_pdf(pdf_path, document_id="doc-002")

    assert result.page_count == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert "First page content." in result.pages[0].text
    assert "Second page content." in result.pages[1].text


def test_reject_pdf_with_no_extractable_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    create_pdf(pdf_path, ["   ", ""])

    with pytest.raises(PDFNoExtractableTextError):
        extract_pdf(pdf_path, document_id="doc-003")


def test_reject_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_pdf(tmp_path / "missing.pdf", document_id="doc-004")


def test_reject_invalid_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "invalid.pdf"
    pdf_path.write_text("This is not a PDF.", encoding="utf-8")

    with pytest.raises(InvalidPDFError):
        extract_pdf(pdf_path, document_id="doc-005")


def test_reject_password_protected_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "protected.pdf"
    document = pymupdf.open()
    document.new_page()
    document.save(
        pdf_path,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
    )
    document.close()

    with pytest.raises(PDFPasswordRequiredError):
        extract_pdf(pdf_path, document_id="doc-006")
