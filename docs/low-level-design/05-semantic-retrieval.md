# Low-Level Design: Semantic Retrieval Service

## 1. Purpose

Define the contract for composing query embedding with PostgreSQL-backed
semantic search, returning ranked, provenance-preserving passages for
downstream evidence-grounded question answering.

The service is a reusable Python component. It does not generate answers or
independently decide whether evidence is sufficient to answer a question.

## 2. Scope

### Included

- Validate query text and retrieval parameters.
- Embed a query using the configured `EmbeddingGenerator`.
- Search the PostgreSQL vector index.
- Optionally restrict retrieval to one document.
- Request additional candidates to allow for duplicate-text suppression.
- Suppress duplicate passage text.
- Return up to `top_k` unique results while preserving original text,
  similarity scores, and provenance.

### Excluded

- PDF extraction and passage chunking.
- Persistence of passage embeddings.
- Evidence-sufficiency classification.
- LLM-based answer generation.
- Citation formatting for generated answers.
- HTTP API and user interface.
- Approximate nearest-neighbor indexing.

## 3. Module and Dependencies

Module:

`src/ai_document_intelligence/retrieval/retrieval_service.py`

The service composes:

- `EmbeddingGenerator`, from
  `ai_document_intelligence.embeddings.embedding_generator`.
- `PostgresVectorIndex` and `SearchResult`, from
  `ai_document_intelligence.retrieval.postgres_vector_index`.

Dependencies are injected into the constructor so the service can be tested
without loading a real embedding model or connecting to a database.

## 4. Public Interface

The public operation is:

`retrieve(query: str, top_k: int = 5, document_id: str | None = None) -> list[SearchResult]`

### Parameters

- `query`: non-empty user query text.
- `top_k`: positive integer specifying the maximum number of unique results.
  Boolean values are not accepted as integers.
- `document_id`: optional non-empty document identifier. When supplied,
  search is restricted to that document.

### Validation behavior

- A non-string or whitespace-only query raises `EmbeddingGenerationError`.
- A non-positive or non-integer `top_k`, including a boolean, raises
  `ValueError`.
- A provided `document_id` that is not a non-empty string raises
  `ValueError`.
- Errors from query embedding or vector search are not silently converted
  into successful empty results.

## 5. Retrieval Algorithm

For a valid request:

1. Embed the query with `EmbeddingGenerator.embed_query()`.
2. Calculate the candidate count using `CANDIDATE_MULTIPLIER = 4` and
   `MAX_CANDIDATES = 200`.
3. Request `min(top_k * 4, 200)` candidates, but never fewer than `top_k`.
4. Pass the query embedding, candidate count, and optional `document_id` to
   `PostgresVectorIndex.search()`.
5. Process candidates in the order returned by the vector index.
6. Normalize candidate text for duplicate comparison by applying Python
   `casefold()` and collapsing whitespace with `split()` and `join()`.
7. Skip empty normalized text and text already encountered.
8. Preserve the first candidate for each normalized text, including its
   original text, score, and provenance.
9. Stop when `top_k` unique results have been collected, or return fewer if
   the candidate set contains fewer unique non-empty passages.

The candidate multiplier is a heuristic, not a guarantee that `top_k` unique
results will always be available. The maximum candidate count limits
over-fetching for large requested result counts.

## 6. Ranking and Duplicate Suppression

The PostgreSQL index ranks candidates by exact cosine similarity, with a
stable passage-ID tie-breaker for equal distances. The retrieval service
preserves this order while removing duplicate text.

Duplicate comparison is case-insensitive and ignores whitespace differences.
It does not perform semantic equivalence detection: passages with different
wording are not considered duplicates merely because they express similar
ideas.

When duplicate text occurs, the first matching result in index ranking order
is retained. The original passage content is not rewritten in the returned
result.

## 7. Document-Level Filtering

When `document_id` is supplied, the service forwards it to the vector index.
The index applies the document filter in SQL before ranking and limiting the
candidate set.

When `document_id` is omitted, retrieval searches across the indexed corpus.
The service does not delete, rewrite, or otherwise mutate indexed records.

## 8. Embedding Compatibility

Query embeddings must belong to the same compatible embedding space as the
stored passage embeddings. The service relies on the configured
`EmbeddingGenerator` and the index's vector validation; it does not inspect
or migrate the model identity of existing database rows.

Changing the embedding model, model revision, or dimension requires an
explicit compatibility and re-indexing decision. The service does not prove
that an existing index was created using the intended model.

## 9. Testing Strategy

Unit tests should cover:

- Successful retrieval and correct forwarding of the query embedding.
- Query validation and exception behavior.
- Positive integer `top_k` validation, including rejection of booleans.
- Optional document ID validation and forwarding.
- Candidate-count calculation for ordinary and large `top_k` values.
- Duplicate suppression for case and whitespace differences.
- Preservation of the first, highest-ranked duplicate result.
- Skipping empty or whitespace-only candidate text.
- Preservation of result ordering, score, and provenance.
- Returning fewer than `top_k` results when unique candidates are exhausted.
- Propagation of embedding and vector-index failures.

Tests should use injected or mocked dependencies and should not require
network access or model downloads.

PostgreSQL search integration tests belong to the vector-index test suite.
End-to-end answer generation is outside this service's test scope.

## 10. Acceptance Criteria

- Query text and parameters are validated.
- Query embeddings are generated using the configured local model.
- Optional document filtering is passed to the vector index.
- Candidate over-fetching follows the documented constants.
- Duplicate suppression is deterministic for the same ordered candidate set.
- Returned results preserve the original text and provenance.
- Failures are not silently represented as successful empty retrievals.
- Unit tests and Ruff checks pass.

## 11. Known Limitations and Future Work

- Duplicate suppression is text-based, not semantic.
- Candidate over-fetching can still yield fewer than `top_k` unique results.
- The service does not evaluate whether evidence is sufficient or conflicting.
- Retrieval quality must be evaluated against a controlled question-and-
  evidence dataset.
- Exact-search latency should be measured before considering HNSW or other
  approximate-index strategies.
- Answer generation, generated-answer citations, API integration, and the
  user interface remain future milestones.
