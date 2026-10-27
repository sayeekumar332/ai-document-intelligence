"""PostgreSQL-backed passage retrieval."""

from ai_document_intelligence.retrieval.postgres_vector_index import (
    PostgresVectorIndex,
    SearchResult,
    VectorIndexError,
)
from ai_document_intelligence.retrieval.retrieval_service import RetrievalService

__all__ = [
    "PostgresVectorIndex",
    "RetrievalService",
    "SearchResult",
    "VectorIndexError",
]
