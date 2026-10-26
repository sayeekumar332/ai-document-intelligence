# Low-Level Design: PostgreSQL Vector Index

## 1. Purpose

Provide persistent vector storage and semantic similarity search for the
AI Document Intelligence Platform using PostgreSQL and pgvector.

The index builds on the existing embedding-generation component and returns
ranked passages with their original source metadata.

## 2. Scope

### Included
- Store embedded passages in PostgreSQL.
- Use pgvector's native vector type.
- Preserve passage identifiers, document identifiers, source names,
  page numbers, and original text.
- Insert or update passages transactionally.
- Delete passages belonging to a document.
- Search by cosine distance.
- Return ranked passages with provenance and similarity scores.
- Validate embedding dimensions, numerical values, and query parameters.
- Preserve data between application executions.
- Test against a real local PostgreSQL database.

### Excluded
- PDF extraction and passage chunking.
- Generating embeddings for queries.
- LLM answer generation.
- OCR and image embeddings.
- Cloud-hosted database deployment.
- Approximate nearest-neighbor indexing in the initial implementation.

## 3. Database Technology

Use PostgreSQL 17 with the pgvector extension.

Proposed Docker image:

`pgvector/pgvector:0.8.7-pg17-bookworm`

Pinning the image version makes development environments reproducible and
avoids silently changing the PostgreSQL or pgvector version.

The database runs locally through Docker Compose. No cloud database or
paid AI service is required.

Proposed local host connection:
- Host: `127.0.0.1`
- Port: `54329`
- Database: `ai_document_intelligence`

Port 54329 is configurable and avoids requiring the host's default
PostgreSQL port.

Persistent database files are managed through a named Docker volume.
Database data, credentials, and local environment files must not be
committed to Git.

## 4. PostgreSQL Extension and Schema

Enable pgvector in the target database:

`CREATE EXTENSION IF NOT EXISTS vector;`

### 4.1 Index metadata

Maintain index metadata containing:
- `schema_version`
- `model_name`
- `embedding_dimension`
- `vector_encoding`
- `distance_metric`
- `pgvector_version`

The metadata identifies the schema and configured embedding space.

The current `EmbeddedPassage` record does not identify the model revision
that produced each vector. The index therefore cannot independently prove
the origin of every incoming vector. The caller must ensure that stored
passages and query embeddings use the configured model and compatible
settings.

Opening an existing index with an incompatible model name, dimension,
or schema version must fail clearly rather than silently mixing vectors.

### 4.2 Passages table

Proposed logical schema:

| Column | Purpose |
|---|---|
| `passage_id` | Primary key identifying a passage |
| `document_id` | Identifier of the source document |
| `source_name` | Original source filename |
| `page_number` | Original page number |
| `text` | Original passage text |
| `embedding` | pgvector `vector(384)` column |

The embedding dimension is configurable at index initialization. The
database schema must use the configured dimension consistently.

Add a B-tree index on `document_id` to support document-level deletion.

Use parameterized SQL for values. Do not interpolate untrusted text into
SQL statements.

## 5. Vector Representation and Similarity

Use pgvector's native `vector(n)` type, with `n` equal to the configured
embedding dimension. Do not manually serialize embeddings into SQLite
BLOBs or manage binary byte ordering in application code.

The first implementation performs exact cosine-distance search.

pgvector represents cosine distance using the `<=>` operator. Rank results
in ascending distance order:

`ORDER BY embedding <=> query_vector`

The similarity score returned by the application is:

`similarity = 1 - cosine_distance`

The Python layer must validate:
- Correct embedding dimensions.
- Finite numeric values.
- Non-zero vector norms.
- Positive `top_k`.
- Consistent model and index configuration.

Do not assume vectors supplied by injected models are normalized.

## 6. Proposed Python Interface

Module:

`src/ai_document_intelligence/retrieval/postgres_vector_index.py`

Public components:

- `PostgresVectorIndex`: manages persistence and vector search.
- `SearchResult`: immutable record containing passage metadata and score.
- `VectorIndexError`: application-level database and validation exception.

Use psycopg 3 as the PostgreSQL client. Keep connection details configurable
through environment variables or an injected connection configuration;
credentials must not be hard-coded into Python source files.

The constructor will accept the database connection configuration,
model name, and embedding dimension.

### `upsert(passages)`

Accept a sequence of `EmbeddedPassage` objects.

Requirements:
- Validate the entire input batch before writing.
- Reject duplicate passage IDs within the batch.
- Validate passage metadata and vectors.
- Use a single database transaction for the batch.
- Insert new passages and update existing records with the same passage ID.
- Roll back the entire batch if any operation fails.

### `delete_document(document_id)`

Delete all passages belonging to the given document and return the number
of deleted records.

### `search(query_embedding, top_k=5)`

Return up to `top_k` records ranked by cosine similarity.

Requirements:
- Validate the query vector and `top_k`.
- Return an empty list for an empty index.
- Use a stable passage-ID tie-breaker for equal distances.
- Return the original text and passage provenance.
- Use parameterized SQL and the pgvector cosine-distance operator.

### `count()`

Return the number of indexed passages.

## 7. Configuration and Secrets

Use a local `.env` file for PostgreSQL development configuration.
Provide a `.env.example` file with placeholder values and instructions.

Required settings:
- PostgreSQL database name.
- PostgreSQL application username.
- PostgreSQL password.
- Host and port.

The `.env` file and actual credentials must remain ignored by Git.

The Compose database must use a persistent named volume and a health check.
Publish the database port only on the local loopback interface by default.

## 8. Transaction and Error Handling

- Batch upserts must be atomic.
- Invalid input must not produce partial writes.
- Existing rows must remain unchanged when a batch rolls back.
- Database connection and query errors must provide useful context.
- Incompatible schema or embedding metadata must fail clearly.
- Query vectors with invalid dimensions, non-finite values, or zero norm
  must be rejected before ranking.
- Connection resources must be closed or returned to a managed pool.
- Passwords and connection strings containing secrets must not appear in
  error messages or logs.

## 9. Testing Strategy

Unit tests must cover vector validation, query parameters, ranking
behavior, and error handling.

PostgreSQL integration tests must cover:
1. Creating the schema and enabling pgvector.
2. Inserting embedded passages.
3. Preserving passage metadata.
4. Reopening the index and retaining data.
5. Upserting an existing passage.
6. Deleting passages by document ID.
7. Empty-index search.
8. Correct cosine-similarity ranking.
9. Stable tie-breaking.
10. Invalid `top_k` and invalid vectors.
11. Duplicate IDs within a batch.
12. Atomic rollback on a failed batch.
13. Model or dimension mismatch.
14. Counting indexed passages.

Use an isolated test database or schema. Tests must not delete or overwrite
ordinary development data.

## 10. Acceptance Criteria

The component is ready when:
- PostgreSQL and pgvector work through the documented local setup.
- Embedded passages persist between application runs.
- Passage provenance is preserved.
- Exact cosine-similarity search is correct and deterministic.
- Upserts are transactional.
- Document deletion works correctly.
- Invalid data and incompatible configuration fail clearly.
- PostgreSQL integration tests pass.
- Ruff, pytest, and dependency checks pass.
- No database files, private documents, or secrets are committed.

## 11. Performance and Future Work

Start with exact cosine-distance search to establish a correctness baseline.

Measure retrieval latency as the corpus grows. Add a pgvector HNSW index
only after the baseline is correct and performance measurements justify it.

Future work may include:
- HNSW indexing and recall/latency evaluation.
- Query latency and throughput benchmarks.
- Incremental document re-indexing.
- Retrieval evaluation against a question-and-evidence dataset.
- Deployment behind an application API.

## 12. Integration with Existing Components

The intended flow is:

1. Extract PDF text.
2. Chunk text into provenance-preserving `Passage` objects.
3. Generate `EmbeddedPassage` objects with `EmbeddingGenerator`.
4. Persist embedded passages through `PostgresVectorIndex`.
5. Embed a user query using the same model configuration.
6. Search PostgreSQL and return ranked passages with source metadata.

Query embedding and grounded answer generation remain separate components.
