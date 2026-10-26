# AI Document Intelligence Platform

A local-first AI application for extracting PDF content, creating semantic
embeddings, and retrieving relevant evidence while preserving document and
page-level provenance.

## Project Goals

- Extract text from PDF documents and preserve page numbers.
- Split extracted text into provenance-preserving passages.
- Generate text embeddings locally.
- Persist embeddings and metadata in PostgreSQL with pgvector.
- Retrieve relevant passages through vector similarity search.
- Build toward evidence-grounded answers with source citations.
- Evaluate retrieval quality and handle insufficient evidence explicitly.

## Current Implementation

- **PDF extraction:** PyMuPDF with explicit error handling.
- **Passage chunking:** configurable, page-aware text chunking.
- **Embedding generation:** Sentence Transformers using
  `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- **Vector storage and search:** PostgreSQL with pgvector, using exact
  cosine-similarity search as the initial retrieval baseline.
- **Testing:** pytest unit and integration tests.
- **Code quality:** Ruff lint checks.

The implementation is developed incrementally. Query processing,
evidence-grounded answer generation, the API, and the user interface remain
subsequent milestones.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| PDF extraction | PyMuPDF |
| Passage chunking | Python |
| Embeddings | Sentence Transformers and PyTorch |
| Database | PostgreSQL |
| Vector operations | pgvector |
| Local database environment | Docker Compose |
| PostgreSQL driver | Psycopg 3 |
| Tests | pytest |
| Linting | Ruff |

## Local Development

See the development guides before starting the database or running tests:

- [Python development and verification commands](docs/development/python-commands.md)
- [PostgreSQL and pgvector setup](docs/development/postgresql-setup.md)

The PostgreSQL setup guide explains local credentials, database initialization,
the isolated integration-test database, and safe container lifecycle commands.

Do not commit `.env` files, database data, model weights, private PDFs, or
generated embedding vectors.

## Design Documentation

### High-level design

- [System overview](docs/high-level-design/01-system-overview.md)

### Low-level design

- [PDF extraction](docs/low-level-design/01-pdf-extraction.md)
- [Passage chunking](docs/low-level-design/02-passage-chunking.md)
- [Embedding generation](docs/low-level-design/03-embedding-generation.md)
- [PostgreSQL vector index](docs/low-level-design/04-local-vector-index.md)

## Verification

Activate the project virtual environment and run:

    python -m ruff check .
    python -m pytest
    python -m pip check

The test suite includes deterministic unit tests and database integration
tests. PostgreSQL integration tests require the local Compose database and
must use the dedicated test database configured in `.env`.

## Engineering Principles

- Prefer local execution without paid AI inference services.
- Preserve source document and page provenance throughout the pipeline.
- Keep extraction, chunking, embeddings, indexing, retrieval, and generation
  as separate components.
- Test error paths and transactional behavior, not only success cases.
- Keep secrets, user documents, model caches, and generated artifacts out of Git.
- Document design decisions and verify changes before merging.
