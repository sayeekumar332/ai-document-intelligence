"""Split extracted PDF pages into overlapping, provenance-preserving passages."""

from dataclasses import dataclass

from ai_document_intelligence.ingestion.pdf_extractor import ExtractedDocument


class InvalidChunkingConfigurationError(ValueError):
    """Raised when passage chunking settings are invalid."""


@dataclass(frozen=True)
class Passage:
    """A text passage linked to its source document and page."""

    passage_id: str
    document_id: str
    source_name: str
    page_number: int
    text: str


def _select_boundary(text: str, start: int, end: int) -> int:
    """Select a paragraph, sentence, or whitespace boundary when possible."""
    minimum_boundary = start + (end - start) // 2
    candidate = text[minimum_boundary:end]

    # Prefer paragraph separators, retaining their original characters.
    paragraph_positions = [
        minimum_boundary + match
        for match in range(len(candidate))
        if candidate.startswith("\n\n", match)
    ]
    if paragraph_positions:
        return paragraph_positions[-1] + 2

    # Prefer sentence-ending punctuation followed by whitespace.
    sentence_positions = [
        minimum_boundary + index + 1
        for index, character in enumerate(candidate[:-1])
        if character in ".!?" and candidate[index + 1].isspace()
    ]
    if sentence_positions:
        return sentence_positions[-1]

    # Fall back to the last whitespace boundary in the permitted window.
    whitespace_positions = [
        index
        for index in range(minimum_boundary, end)
        if text[index].isspace()
    ]
    if whitespace_positions:
        return whitespace_positions[-1] + 1

    return end


def chunk_document(
    document: ExtractedDocument,
    max_chars: int = 800,
    overlap_chars: int = 120,
) -> list[Passage]:
    """Split each page into deterministic, overlapping passages."""
    if max_chars <= 0:
        raise InvalidChunkingConfigurationError(
            "max_chars must be greater than zero."
        )
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise InvalidChunkingConfigurationError(
            "overlap_chars must be non-negative and less than max_chars."
        )

    passages: list[Passage] = []

    for page in document.pages:
        text = page.text
        if not text.strip():
            continue

        start = 0
        page_passage_index = 0

        while start < len(text):
            end = min(start + max_chars, len(text))

            if end < len(text):
                end = _select_boundary(text, start, end)

            passage_text = text[start:end]

            if passage_text.strip():
                passage_id = (
                    f"{document.document_id}:p{page.page_number}:c{page_passage_index}"
                )
                passages.append(
                    Passage(
                        passage_id=passage_id,
                        document_id=document.document_id,
                        source_name=document.source_name,
                        page_number=page.page_number,
                        text=passage_text,
                    )
                )
                page_passage_index += 1

            if end >= len(text):
                break

            start = max(start + 1, end - overlap_chars)

    return passages
