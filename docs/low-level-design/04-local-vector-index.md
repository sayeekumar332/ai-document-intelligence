# Low-Level Design: Local Vector Index

## 1. Purpose

Provide persistent local storage and exact similarity search for
provenance-preserving embedded passages in the AI Document Intelligence
Platform.

The component builds on the existing embedding-generation interface and
must support retrieval of relevant passages with their original source
metadata.

## 2. Scope

### Included
- Persist embedded passages locally.
- Preserve passage identifiers, document identifiers, source names,
  page numbers, and original text.
- Store embedding vectors in a defined binary representation.
- Validate embedding dimensions and numerical values.
- Insert or update passages atomically.
- Delete passages belonging to a document.
- Search stored embeddings by cosine similarity.
- Return the highest-scoring passages with their provenance.
- Reopen an index and retain its data between program executions.
- Test storage and retrieval using temporary database files.

### Excluded
- PDF extraction and passage chunking.
- Generating embeddings for text queries.
- Approximate nearest-neighbor indexing.
- Cloud vector databases.
- LLM answer generation and response synthesis.
- OCR and image embeddings.

## 3. Storage Technology

Use Python's built-in `sqlite3` module for persistence.

Reasons:
- No separate database server is required.
- Database transactions provide atomic batch updates.
- Passage metadata can be queried using SQL.
- The database is a local file.
- No additional package dependency is required for persistence.

Proposed default database path:

`data/vector-index.sqlite3`

The path must remain configurable so tests can use temporary files and
applications can choose a different storage location.

The `data/` directory is already ignored by the project's `.gitignore`.
The database and generated embedding data must not be committed.

## 4. Database Schema

### 4.1 Index metadata

Maintain index-level metadata containing:
- `schema_version`
- `model_name`
- `embedding_dimension`
- `vector_encoding`

The metadata identifies the database schema and the configured
embedding model and dimension used to construct the index.

The current `EmbeddedPassage` record does not contain a model identifier
or model revision. Therefore, the index cannot independently verify the
origin of each incoming vector. The caller must ensure that inserted
passages and search query vectors were generated using the index's
configured model and compatible embedding settings.

The initial vector encoding is little-endian IEEE 754 float32.

When an existing index is opened, its stored model name and dimension
must be checked against the requested configuration. Incompatible
configuration must produce a clear application-level error rather than
silently mixing embeddings from different model spaces.

### 4.2 Passages table

Proposed logical schema:

| Column | Purpose |
|---|---|
| `passage_id` | Primary key identifying a passage |
| `document_id` | Identifier of the source document |
| `source_name` | Original source filename |
| `page_number` | Original page number |
| `text` | Original passage text |
| `embedding` | Embedding stored as a binary BLOB |

Create an index on `document_id` to support document-level deletion.

The `passage_id` remains the unique passage key. Re-indexing a passage
with the same ID updates its stored text, metadata, and embedding.

## 5. Vector Representation

Store each vector as a sequence of float32 values in a SQLite BLOB.

The representation must:
- Use the configured embedding dimension.
- Use little-endian byte ordering.
- Have exactly four bytes per vector component.
- Be encoded and decoded consistently.
- Reject vectors with incorrect dimensions.
- Reject NaN, infinity, and zero-norm vectors for cosine similarity.
- Detect values that cannot be represented safely as float32.

The binary representation is an internal storage format, not a public
API. A future storage implementation may use a different representation
provided its interface and migration requirements are explicit.

## 6. Proposed Python Interface

Proposed module:

`src/ai_document_intelligence/retrieval/local_vector_index.py`

Proposed components:

- `LocalVectorIndex`: manages local persistence and similarity search.
- `SearchResult`: immutable record containing passage metadata and
  its similarity score.
- `VectorIndexError`: application-level error for index configuration,
  storage, and vector validation failures.

Proposed constructor:

`LocalVectorIndex(db_path, model_name, embedding_dimension=384)`

Proposed operations:

### `upsert(passages)`

Accept a sequence of `EmbeddedPassage` objects and insert or update
their records.

Requirements:
- Validate all input records before writing.
- Reject duplicate passage IDs within the same input batch.
- Require the configured vector dimension.
- Validate that each vector contains only finite values and has a
  non-zero norm.
- Execute the complete batch in a transaction.
- Roll back the entire batch if any write fails.

### `delete_document(document_id)`

Delete all indexed passages belonging to the specified document.

Return the number of deleted passages.

### `search(query_embedding, top_k=5)`

Accept a query embedding and return up to `top_k` matching passages,
ranked by cosine similarity in descending order.

Requirements:
- Require a positive `top_k`.
- Validate query dimension, finiteness, and non-zero norm.
- Require the query to have been generated in the same embedding space
  as the index.
- Return an empty list when the index contains no passages.
- Use `passage_id` as a stable tie-breaker for equal scores.
- Return original passage text and provenance with each score.

### `count()`

Return the number of passages currently stored in the index.

## 7. Similarity Calculation

For query vector `q` and stored vector `v`, cosine similarity is:

`similarity(q, v) = dot(q, v) / (norm(q) * norm(v))`

The initial implementation uses exact cosine similarity for every
stored passage.

Scores are ordered from highest to lowest. The implementation must
not assume that injected model outputs are normalized, even though the
current embedding generator requests normalized embeddings.

This approach provides an exact baseline but requires a scan of the
stored vectors for each query. Its performance must be measured before
choosing a more sophisticated indexing method.

## 8. Transaction and Error Handling

- A batch upsert must be atomic.
- Invalid input must not leave a partially written batch.
- Existing records must remain unchanged if an upsert fails.
- Database failures must be reported with useful context.
- Opening an index with incompatible model metadata must fail clearly.
- Invalid query vectors must be rejected before similarity ranking.
- Missing databases may be initialized with the requested configuration.
- The index must not silently mix embedding dimensions or model spaces.

## 9. Testing Strategy

Unit tests must cover:
1. Creating a new index.
2. Persisting passages and reopening the database.
3. Preserving all passage metadata.
4. Upserting an existing passage.
5. Deleting passages by document ID.
6. Empty index search.
7. Correct similarity ranking.
8. Stable ordering for equal scores.
9. Invalid `top_k`.
10. Invalid dimensions and non-finite values.
11. Zero-norm vectors.
12. Duplicate IDs within an upsert batch.
13. Atomic rollback when a batch fails.
14. Model or dimension mismatch when reopening an index.
15. Counting stored passages.

Use temporary database paths in tests so test data is not written to
the repository or to the application's default data directory.

## 10. Acceptance Criteria

The component is ready when:
- Embedded passages persist between program executions.
- Passage provenance is preserved.
- Vector encoding and decoding are tested.
- Upserts and document deletion work correctly.
- Similarity ranking is correct and deterministic.
- Invalid data and incompatible configurations fail clearly.
- Batch operations are transactional.
- Unit tests cover success and failure paths.
- Ruff, pytest, and dependency checks pass.
- No generated database, private PDF, or embedding vector data is
  committed.

## 11. Performance and Future Work

The initial implementation uses exact search over locally stored
vectors. It is intended as a correctness baseline for local corpora.

Future work may evaluate:
- Query latency as the corpus grows.
- Batch loading and database read performance.
- Specialized vector indexes such as FAISS or HNSW-based solutions.
- Incremental re-indexing and document replacement.
- Retrieval quality using a controlled question-and-evidence dataset.

A specialized vector index must be introduced only after performance
measurement demonstrates a need and an explicit design decision is made.

## 12. Integration with Existing Components

The intended processing flow is:

1. Extract PDF text.
2. Chunk text into provenance-preserving `Passage` objects.
3. Generate `EmbeddedPassage` objects using `EmbeddingGenerator`.
4. Persist the embedded passages using `LocalVectorIndex`.
5. Embed a user query using the same embedding model.
6. Search the index and return ranked passages with source metadata.

Query embedding and grounded answer generation are consumers of this
index; they are not implemented by the storage component itself.
