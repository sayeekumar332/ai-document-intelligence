"""Unit tests for the retrieval service."""

from typing import cast

import pytest

from ai_document_intelligence.embeddings.embedding_generator import (
    EmbeddingGenerationError,
    EmbeddingGenerator,
)
from ai_document_intelligence.retrieval import (
    PostgresVectorIndex,
    RetrievalService,
    SearchResult,
    VectorIndexError,
)


class FakeEmbeddingGenerator:
    def __init__(
        self,
        result: tuple[float, ...] = (0.6, 0.8),
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.queries: list[str] = []

    def embed_query(self, query: str) -> tuple[float, ...]:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result


class FakeVectorIndex:
    def __init__(
        self,
        results: list[SearchResult] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.embeddings: list[tuple[float, ...]] = []
        self.top_ks: list[int] = []
        self.document_ids: list[str | None] = []

    def search(
        self,
        query_embedding: tuple[float, ...],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        self.embeddings.append(query_embedding)
        self.top_ks.append(top_k)
        self.document_ids.append(document_id)
        if self.error is not None:
            raise self.error
        return self.results


def make_result(
    passage_id: str,
    *,
    score: float,
    text: str,
    page_number: int,
) -> SearchResult:
    return SearchResult(
        passage_id=passage_id,
        document_id="doc-1",
        source_name="manual.pdf",
        page_number=page_number,
        text=text,
        score=score,
    )


def make_service(
    generator: FakeEmbeddingGenerator,
    index: FakeVectorIndex,
) -> RetrievalService:
    return RetrievalService(
        embedding_generator=cast(EmbeddingGenerator, generator),
        vector_index=cast("PostgresVectorIndex", index),
    )


def test_retrieve_embeds_query_and_forwards_top_k() -> None:
    expected = [
        make_result(
            "p1", score=0.94, text="Control unit overview", page_number=2
        ),
        make_result(
            "p2", score=0.81, text="Control signals", page_number=3
        ),
    ]
    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex(results=expected)
    service = make_service(generator, index)

    actual = service.retrieve("What is the control unit?", top_k=2)

    assert actual == expected
    assert generator.queries == ["What is the control unit?"]
    assert index.embeddings == [(0.6, 0.8)]
    assert index.top_ks == [8]
    assert index.document_ids == [None]
    assert actual[0].score > actual[1].score
    assert actual[0].source_name == "manual.pdf"
    assert actual[0].page_number == 2
    assert actual[0].text == "Control unit overview"


@pytest.mark.parametrize("query", ["", "  ", "\n\t", None, 123])
def test_retrieve_rejects_invalid_query(query: object) -> None:
    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex()
    service = make_service(generator, index)

    with pytest.raises(EmbeddingGenerationError, match="non-empty string"):
        service.retrieve(query)  # type: ignore[arg-type]

    assert generator.queries == []
    assert index.embeddings == []


def test_retrieve_propagates_embedding_error() -> None:
    error = EmbeddingGenerationError("model unavailable")
    generator = FakeEmbeddingGenerator(error=error)
    index = FakeVectorIndex()
    service = make_service(generator, index)

    with pytest.raises(EmbeddingGenerationError, match="model unavailable"):
        service.retrieve("A valid query")

    assert index.embeddings == []


def test_retrieve_propagates_index_error() -> None:
    error = VectorIndexError("index unavailable")
    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex(error=error)
    service = make_service(generator, index)

    with pytest.raises(VectorIndexError, match="index unavailable"):
        service.retrieve("A valid query")

    assert index.embeddings == [(0.6, 0.8)]


@pytest.mark.parametrize("top_k", [0, -1, True, False, 1.5, "5", None])
def test_retrieve_rejects_invalid_top_k(top_k: object) -> None:
    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex()
    service = make_service(generator, index)

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        service.retrieve("A valid query", top_k=top_k)  # type: ignore[arg-type]

    assert generator.queries == []
    assert index.embeddings == []


def test_retrieve_suppresses_normalized_duplicates_and_preserves_best() -> None:
    best = make_result(
        "p1",
        score=0.95,
        text="The Control Store\nselects the next microinstruction.",
        page_number=4,
    )
    duplicate = make_result(
        "p2",
        score=0.82,
        text="  the control store selects   the next microinstruction. ",
        page_number=9,
    )
    other = make_result(
        "p3",
        score=0.75,
        text="The execution unit performs arithmetic operations.",
        page_number=5,
    )

    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex(results=[best, duplicate, other])
    service = make_service(generator, index)

    actual = service.retrieve("What does the control store do?", top_k=2)

    assert actual == [best, other]
    assert [result.passage_id for result in actual] == ["p1", "p3"]
    assert actual[0].text == best.text
    assert actual[0].page_number == 4
    assert actual[0].source_name == "manual.pdf"
    assert actual[0].score == 0.95
    assert index.top_ks == [8]


def test_retrieve_returns_fewer_results_when_not_enough_unique_candidates() -> None:
    first = make_result(
        "p1",
        score=0.9,
        text="Same passage",
        page_number=1,
    )
    duplicate = make_result(
        "p2",
        score=0.8,
        text=" SAME   PASSAGE ",
        page_number=2,
    )

    service = make_service(
        FakeEmbeddingGenerator(),
        FakeVectorIndex(results=[first, duplicate]),
    )

    actual = service.retrieve("Find the passage", top_k=3)

    assert actual == [first]


@pytest.mark.parametrize("document_id", ["", "  ", "\n", 123, False])
def test_retrieve_rejects_invalid_document_id(document_id: object) -> None:
    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex()
    service = make_service(generator, index)

    with pytest.raises(ValueError, match="document_id must be a non-empty string"):
        service.retrieve(
            "A valid query",
            document_id=document_id,  # type: ignore[arg-type]
        )

    assert generator.queries == []
    assert index.embeddings == []


def test_retrieve_forwards_document_filter() -> None:
    expected = make_result(
        "p1", score=0.94, text="Scoped evidence", page_number=2
    )
    generator = FakeEmbeddingGenerator()
    index = FakeVectorIndex(results=[expected])
    service = make_service(generator, index)

    actual = service.retrieve(
        "Find evidence",
        top_k=1,
        document_id="doc-1",
    )

    assert actual == [expected]
    assert index.top_ks == [4]
    assert index.document_ids == ["doc-1"]


def test_retrieve_skips_empty_passages() -> None:
    empty = make_result(
        "p1",
        score=0.95,
        text=" \n\t ",
        page_number=1,
    )
    useful = make_result(
        "p2",
        score=0.8,
        text="Useful evidence",
        page_number=2,
    )

    service = make_service(
        FakeEmbeddingGenerator(),
        FakeVectorIndex(results=[empty, useful]),
    )

    assert service.retrieve("Find evidence", top_k=1) == [useful]
