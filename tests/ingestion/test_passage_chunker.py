"""Unit tests for PDF passage chunking."""

import pytest

from ai_document_intelligence.ingestion.passage_chunker import (
    InvalidChunkingConfigurationError,
    chunk_document,
)
from ai_document_intelligence.ingestion.pdf_extractor import (
    ExtractedDocument,
    ExtractedPage,
)


def make_document(*page_texts: str) -> ExtractedDocument:
    """Build a document for deterministic chunking tests."""
    return ExtractedDocument(
        document_id="test-document",
        source_name="test.pdf",
        pages=[
            ExtractedPage(page_number=index, text=text)
            for index, text in enumerate(page_texts, start=1)
        ],
        page_count=len(page_texts),
    )


def test_short_page_produces_one_passage() -> None:
    document = make_document("A short page of text.")

    passages = chunk_document(document)

    assert len(passages) == 1
    assert passages[0].text == "A short page of text."
    assert passages[0].page_number == 1


def test_page_exactly_maximum_size_produces_one_passage() -> None:
    document = make_document("x" * 800)

    passages = chunk_document(document)

    assert len(passages) == 1
    assert len(passages[0].text) == 800


def test_passages_never_exceed_maximum_size() -> None:
    document = make_document("word " * 500)

    passages = chunk_document(document)

    assert len(passages) > 1
    assert all(len(passage.text) <= 800 for passage in passages)


def test_adjacent_passages_overlap() -> None:
    document = make_document("x" * 2000)

    passages = chunk_document(document)

    assert len(passages) > 1
    for previous, current in zip(passages, passages[1:]):
        assert previous.text[-120:] == current.text[:120]


def test_prefers_whitespace_boundary() -> None:
    document = make_document(("alpha " * 200).strip())

    passages = chunk_document(document)

    assert len(passages) > 1
    assert passages[0].text[-1].isspace()


def test_long_token_is_split_when_no_whitespace_exists() -> None:
    document = make_document("x" * 2000)

    passages = chunk_document(document)

    assert all(len(passage.text) <= 800 for passage in passages)
    assert (
        "".join(
            passage.text if index == 0 else passage.text[120:]
            for index, passage in enumerate(passages)
        )
        == "x" * 2000
    )


def test_empty_and_whitespace_only_pages_are_skipped() -> None:
    document = make_document("", " \t\n ", "Useful content.")

    passages = chunk_document(document)

    assert len(passages) == 1
    assert passages[0].page_number == 3


def test_page_provenance_and_order_are_preserved() -> None:
    document = make_document("First page.", "Second page.")

    passages = chunk_document(document)

    assert [passage.page_number for passage in passages] == [1, 2]
    assert [passage.text for passage in passages] == [
        "First page.",
        "Second page.",
    ]
    assert all(passage.document_id == "test-document" for passage in passages)
    assert all(passage.source_name == "test.pdf" for passage in passages)


def test_passage_ids_are_stable_and_unique() -> None:
    document = make_document("x" * 2000, "Another page.")

    first_run = chunk_document(document)
    second_run = chunk_document(document)

    first_ids = [passage.passage_id for passage in first_run]

    assert first_ids == [passage.passage_id for passage in second_run]
    assert len(first_ids) == len(set(first_ids))


@pytest.mark.parametrize(
    ("max_chars", "overlap_chars"),
    [
        (0, 0),
        (-1, 0),
        (800, -1),
        (800, 800),
        (100, 100),
    ],
)
def test_invalid_configuration_is_rejected(
    max_chars: int,
    overlap_chars: int,
) -> None:
    document = make_document("Some content.")

    with pytest.raises(InvalidChunkingConfigurationError):
        chunk_document(
            document,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )


def test_source_text_is_not_mutated() -> None:
    original_text = "  Preserve   internal whitespace.  "
    document = make_document(original_text)

    chunk_document(document)

    assert document.pages[0].text == original_text


def test_prefers_paragraph_boundary() -> None:
    text = ("First paragraph sentence. " * 12).strip()
    text += "\n\n"
    text += ("Second paragraph sentence. " * 20).strip()

    passages = chunk_document(
        make_document(text),
        max_chars=400,
        overlap_chars=40,
    )

    assert len(passages) > 1
    assert len(passages[0].text) <= 400
    assert passages[0].text.endswith("\n\n")


def test_prefers_sentence_boundary_when_no_paragraph_boundary_exists() -> None:
    text = ("A complete sentence. " * 30).strip()

    passages = chunk_document(
        make_document(text),
        max_chars=200,
        overlap_chars=20,
    )

    assert len(passages) > 1
    assert passages[0].text.rstrip().endswith(".")


def test_boundary_selection_preserves_all_source_characters() -> None:
    text = (
        "First sentence. Second sentence.\n\n"
        "Third sentence continues here. Fourth sentence ends here."
    )

    passages = chunk_document(
        make_document(text),
        max_chars=35,
        overlap_chars=8,
    )

    reconstructed = "".join(
        passage.text if index == 0 else passage.text[8:]
        for index, passage in enumerate(passages)
    )

    assert reconstructed == text
