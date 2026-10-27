# AI Document Intelligence Platform — System Overview

## 1. Purpose

Build a local-first application that allows users to ask questions about
PDF documents and receive answers grounded in retrieved document evidence.

The system must preserve source-document and page-level provenance throughout
the processing pipeline so that answers can be traced back to their evidence.

## 2. Primary Objectives

- Extract text from PDF documents while preserving page numbers.
- Divide extracted content into searchable passages.
- Generate semantic embeddings locally.
- Persist passage metadata and embeddings in PostgreSQL using pgvector.
- Retrieve passages relevant to a user's question using vector similarity.
- Generate answers grounded in retrieved evidence.
- Display citations identifying the source document and page.
- Handle invalid documents and insufficient or conflicting evidence explicitly.
- Evaluate extraction, retrieval, and answer quality through automated tests
  and a controlled evaluation corpus.
- Provide a Python API and, in a later phase, a simple user interface.

## 3. System Scope

The initial implementation targets text-based PDFs. Scanned PDFs requiring
optical character recognition (OCR) are outside the initial scope unless
introduced through a later design decision.

The platform is developed incrementally. PDF extraction, passage chunking,
and embedding generation form the ingestion pipeline. PostgreSQL with
pgvector provides persistent vector storage and semantic search.

Query embedding and semantic retrieval are implemented components.
Evidence-grounded answer generation, the API, and the user interface remain
subsequent milestones. The retrieval service is not yet an end-to-end
question-answering application.

## 4. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.12 |
| PDF extraction | PyMuPDF |
| Passage chunking | Python |
| Embedding generation | Sentence Transformers with PyTorch |
| Initial embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding dimension | 384 |
| Relational database | PostgreSQL 17 |
| Vector operations | pgvector |
| Local database environment | Docker Compose |
| PostgreSQL client | Psycopg 3 |
| Unit and integration testing | pytest |
| Linting and code checks | Ruff |
| Future language model runtime | Ollama |
| Future backend API | FastAPI |
| Continuous integration | GitHub Actions |

PostgreSQL stores passage metadata and embeddings. pgvector supplies the
native vector type and similarity operators.

The initial retrieval implementation uses exact cosine-similarity search.
Approximate nearest-neighbor indexing, such as HNSW, may be introduced after
correctness is established and performance measurements justify it.

## 5. High-Level Architecture

The platform consists of the following logical components:

### 5.1 Document ingestion

Accept a PDF document, validate that it can be processed, and extract its
text page by page.

### 5.2 Passage chunking

Divide extracted page text into passages while preserving the document ID,
source filename, and original one-based page number.

### 5.3 Embedding generation

Generate a numerical embedding for each passage using the configured local
Sentence Transformers model. Preserve the passage text and provenance in
each embedding result.

### 5.4 Vector storage and retrieval

Persist embedded passages in PostgreSQL using pgvector. The implemented
`PostgresVectorIndex` performs exact cosine-distance search and returns ranked
passages with their text, similarity scores, and source metadata. Search can
optionally be restricted to a single document using `document_id`.

The `RetrievalService` embeds a non-empty user query with the configured
`EmbeddingGenerator`, requests an expanded candidate set from the vector
index, and suppresses duplicate passage text before returning up to `top_k`
results. Duplicate comparison is case-insensitive and whitespace-normalized;
the original passage text and provenance are preserved in returned results.

Exact search remains the correctness baseline. Approximate-index optimization
is a separate performance decision.

### 5.5 Evidence-grounded answer generation

A future answer-generation component will consume retrieved passages, assess
whether sufficient evidence is available, and generate an answer supported
by the supplied evidence.

It must explicitly handle insufficient or conflicting evidence rather than
present unsupported claims as document facts.

### 5.6 API and user interface

Future components will expose document ingestion and question-answering
operations through an API and a simple user interface.

These components must preserve the separation between ingestion, retrieval,
and answer generation.

## 6. High-Level Processing Flow

The intended end-to-end workflow is:

1. Accept a PDF document.
2. Validate that the document can be opened and processed.
3. Extract text page by page and preserve page numbers.
4. Divide extracted text into passages while retaining source metadata.
5. Generate embeddings for the passages.
6. Store the passages, metadata, and vectors in PostgreSQL with pgvector.
7. Embed a user's query using the same configured embedding model.
8. Retrieve ranked passages using exact cosine-similarity search, optionally
   restricted to a selected document.
9. Suppress duplicate passage text and return up to the requested number of
   unique results, subject to candidate availability.
10. In a future milestone, assess evidence sufficiency and generate an
    evidence-grounded answer.
11. In a future API or user interface, return the answer with source-document
    and page citations.

The ingestion and retrieval components remain independently testable.

## 7. Failure and Evidence Requirements

- Invalid or unreadable PDFs must produce a clear error.
- PDFs with no extractable text must not be treated as successfully extracted.
- Page numbers must remain associated with their source text.
- Passage IDs must remain stable for the same input and chunking configuration.
- Stored vectors and query embeddings must use compatible model settings.
- Invalid vectors and incompatible index configuration must be rejected.
- Database write failures must not leave partially written batches.
- Answers must not present unsupported claims as document facts.
- Insufficient or conflicting evidence must be handled explicitly.
- Retrieved evidence must retain enough provenance to support source citations.

## 8. Privacy and Reproducibility

The application is intended to process documents and generate embeddings
locally by default. The initial database runs locally through Docker Compose.

- Database credentials must be supplied through local environment settings.
- Actual `.env` files must not be committed.
- The development database and integration-test database must remain separate.
- Private PDFs must remain outside version control.
- Model weights, generated vectors, database files, and caches must not
  be committed.
- Database integration tests must use the dedicated test database.
- Dependencies, environment setup, and verification commands must be documented.
- Database volumes must be preserved unless data deletion is intentional.

## 9. Implementation Sequence

1. PDF extraction and validation.
2. Passage chunking and source metadata preservation.
3. Local embedding generation.
4. PostgreSQL and pgvector configuration.
5. Persistent vector indexing and exact similarity search.
6. Query embedding and semantic retrieval, including optional document-level
   filtering and duplicate-text suppression.
7. Retrieval evaluation and refinement using a controlled question-and-
   evidence dataset.
8. Evidence-grounded answer generation and explicit handling of insufficient
   or conflicting evidence.
9. API and user interface.
10. Continuous integration and documentation refinement.

Each milestone should be designed, implemented, tested, and reviewed before
being integrated into the main branch.

## 10. Acceptance Principles

Each component must have a documented interface and automated tests.

The platform must:
- Preserve source traceability throughout ingestion and retrieval.
- Persist embeddings and passage metadata reliably.
- Return relevant passages with deterministic ranking behavior.
- Handle malformed input, incompatible configuration, and database failures.
- Demonstrate retrieval behavior on both answerable and insufficient-evidence
  questions before grounded answer generation is considered complete.
- Keep secrets and private data outside version control.
- Provide reproducible development and verification instructions.

Detailed contracts and testing requirements are maintained in the low-level
design documents.
