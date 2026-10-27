"""Compose query embedding with PostgreSQL-backed semantic retrieval."""

from ai_document_intelligence.embeddings.embedding_generator import (
    EmbeddingGenerationError,
    EmbeddingGenerator,
)
from ai_document_intelligence.retrieval.postgres_vector_index import (
    PostgresVectorIndex,
    SearchResult,
)


class RetrievalService:
    """Embed queries and retrieve ranked, duplicate-suppressed passages."""

    CANDIDATE_MULTIPLIER = 4
    MAX_CANDIDATES = 200

    def __init__(
        self,
        *,
        embedding_generator: EmbeddingGenerator,
        vector_index: PostgresVectorIndex,
    ) -> None:
        self.embedding_generator = embedding_generator
        self.vector_index = vector_index

    @staticmethod
    def _normalize_for_comparison(text: str) -> str:
        """Normalize text for duplicate detection without changing evidence."""
        return " ".join(text.casefold().split())

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        """Return unique passages globally or from one selected document."""
        if not isinstance(query, str) or not query.strip():
            raise EmbeddingGenerationError(
                "Query must be a non-empty string."
            )

        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if document_id is not None and (
            not isinstance(document_id, str) or not document_id.strip()
        ):
            raise ValueError(
                "document_id must be a non-empty string when provided."
            )

        query_embedding = self.embedding_generator.embed_query(query)

        candidate_k = min(
            top_k * self.CANDIDATE_MULTIPLIER,
            self.MAX_CANDIDATES,
        )
        candidate_k = max(top_k, candidate_k)

        candidates = self.vector_index.search(
            query_embedding,
            top_k=candidate_k,
            document_id=document_id,
        )

        unique_results: list[SearchResult] = []
        seen_text: set[str] = set()

        # The index ranks results first, so the first duplicate is the
        # highest-ranked occurrence and retains its original provenance.
        for result in candidates:
            normalized_text = self._normalize_for_comparison(result.text)

            if not normalized_text or normalized_text in seen_text:
                continue

            seen_text.add(normalized_text)
            unique_results.append(result)

            if len(unique_results) == top_k:
                break

        return unique_results
