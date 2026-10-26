"""PostgreSQL-backed passage retrieval."""

from ai_document_intelligence.retrieval.postgres_vector_index import (
    PostgresVectorIndex,
    SearchResult,
    VectorIndexError,
)

__all__ = [
    "PostgresVectorIndex",
    "SearchResult",
    "VectorIndexError",
]
