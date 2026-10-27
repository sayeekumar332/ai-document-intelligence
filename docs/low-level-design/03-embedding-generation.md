# Low-Level Design: Embedding Generation

## 1. Purpose

Convert provenance-preserving PDF passages into dense numerical vectors for semantic retrieval in the AI Document Intelligence Platform.

The component runs locally after its model and dependencies are available. It does not require paid AI APIs.

## 2. Scope

### Included
- Generate embeddings for passage text.
- Support batch processing.
- Preserve passage identifiers and source provenance.
- Validate embedding output shape and numerical values.
- Configure the model identifier, expected dimension, batch size, and optional device.
- Allow an embedding model to be injected for deterministic unit tests.
- Load the model lazily and reuse the loaded instance.
- Support offline model loading.
- Provide an optional integration test using the actual local model.

### Excluded
- Vector database or index implementation.
- Similarity search and ranking.
- LLM answer generation.
- OCR and image embeddings.
- Model-weight downloads during unit tests or offline inference.

## 3. Initial Model

Use `sentence-transformers/all-MiniLM-L6-v2` as the initial baseline.

- Model identifier: `sentence-transformers/all-MiniLM-L6-v2`
- Expected embedding dimension: 384
- Intended use: English text semantic similarity and retrieval
- Runtime: Sentence Transformers with PyTorch
- Execution: local inference after the model is available in the local cache

The model identifier and expected dimension are configurable through `EmbeddingGenerator` constructor parameters rather than being scattered throughout the application.

## 4. Input and Output

Input: a sequence of existing `Passage` objects from `ai_document_intelligence.ingestion.passage_chunker`.

Each passage includes:
- `passage_id`
- `document_id`
- `source_name`
- `page_number`
- `text`

Output: an immutable `EmbeddedPassage` record for each embedded passage containing:
- `passage_id`
- `document_id`
- `source_name`
- `page_number`
- `text`
- `embedding`

The embedding is represented as a tuple of floating-point values. The output order matches the input order.

The embedding component preserves the original passage text and provenance.

## 5. Module and Interface

Module:

`src/ai_document_intelligence/embeddings/embedding_generator.py`

Public components:
- `EmbeddingGenerator`: configures the model and generates embeddings.
- `EmbeddedPassage`: immutable result record containing the embedding and passage metadata.
- `EmbeddingGenerationError`: application-level exception for model loading, encoding, and output-validation failures.
- `DEFAULT_MODEL_NAME` and `DEFAULT_EMBEDDING_DIMENSION`: default model settings.

The `EmbeddingGenerator` constructor accepts:
- `model_name`: model identifier.
- `device`: optional execution device.
- `expected_dimension`: required vector dimension.
- `batch_size`: encoding batch size.
- `model`: optional injected model implementing the required encoding interface.
- `offline`: whether model loading must use locally available files only.

The `generate(passages)` method accepts a sequence of `Passage` objects and returns a list of `EmbeddedPassage` objects.

The model is loaded lazily when non-empty input first requires encoding. An injected model avoids loading a real model in unit tests.

## 6. Validation and Error Handling

- Empty input returns an empty list without loading the model.
- Empty or whitespace-only passage text is rejected.
- Empty model identifiers, non-positive expected dimensions, and non-positive batch sizes are rejected.
- The number of returned vectors must equal the number of input passages.
- Every vector must have the configured dimension.
- Every vector value must be finite.
- Model loading and encoding failures are wrapped in `EmbeddingGenerationError` with contextual information.
- Input passages are not mutated.
- Output records are immutable.

## 7. Performance and Resource Management

- Passages are encoded in batches using the configured batch size.
- The loaded model instance is reused.
- CPU execution can be selected explicitly; another device can be configured where supported.
- CPU and Apple Silicon MPS execution should be benchmarked before selecting a production default.
- GPU execution should not be assumed to be faster for small batches.
- Model weights and caches must remain outside version control.

## 8. Offline Operation and Privacy

The initial model may require an internet connection for its first download.

After model files and dependencies are available locally:
- Embedding generation does not require a paid service.
- Inference is performed locally; passage text is not sent to an external inference API by this component.
- Offline mode passes `local_files_only=True` to the Sentence Transformers model loader.
- Missing local model files must cause a clear loading failure rather than a fallback network download.

## 9. Testing Strategy

### Unit tests

Unit tests use a mocked embedding model and cover:
- Single and multiple passages.
- Preserved output order and passage provenance.
- Empty input.
- Empty or whitespace-only passage text.
- Invalid configuration.
- Incorrect vector count.
- Incorrect vector dimensions.
- Non-finite vector values.
- Model encoding failures.
- Immutable output records.
- Offline model-loading configuration.

### Integration test

The optional real-model integration test verifies:
- The selected model is available in the local cache.
- Real offline inference succeeds.
- Output count and provenance are correct.
- The embedding dimension is correct.
- All vector values are finite.

The test checks the cache using local-only model lookup and skips if the model is not available. It does not intentionally download model weights.

## 10. Acceptance Criteria

The component is ready when:
- Its public interface and configuration are documented.
- Unit tests cover success and failure paths.
- Passage provenance and ordering are preserved.
- Output dimensions and numerical values are validated.
- Model loading is lazy, reusable, and injectable.
- Offline mode is supported.
- Ruff and pytest pass.
- Model weights, private documents, and generated vectors are not committed.

## 11. Dependencies

The project declares:

`sentence-transformers>=5.0,<6`

This version range constrains the dependency to the 5.x major release line. The implementation has been tested locally with Python 3.12 and Sentence Transformers 5.7.0 on Apple Silicon. Compatibility should be revalidated when dependency versions or the target environment change.

## 12. Integration with Vector Retrieval

The embedding-generation component produces `EmbeddedPassage` records.
It does not persist vectors, perform similarity search, or generate answers.

The downstream vector-index design is documented in:

`docs/low-level-design/04-local-vector-index.md`

That design specifies PostgreSQL with pgvector for persistent passage
storage and cosine-similarity retrieval.

### Intended integration flow

1. Extract PDF text and create provenance-preserving `Passage` objects.
2. Generate `EmbeddedPassage` records using `EmbeddingGenerator`.
3. Pass the embedded passages to `PostgresVectorIndex` for persistence.
4. Generate an embedding for a user's query using the same configured
   model and compatible embedding settings.
5. Search the vector index and return ranked passages with their original
   text, document identifiers, source filenames, and page numbers.
6. Supply retrieved evidence to a separately implemented answer-generation
   component.

### Embedding-space compatibility

The current `EmbeddedPassage` record does not contain a model identifier
or model revision. The vector index therefore cannot independently prove
which model produced each incoming vector.

The calling application is responsible for ensuring that stored passage
vectors and query vectors belong to the same configured embedding space.
Changing the model or embedding dimension requires explicit index
configuration and compatibility handling.

### Downstream work

- Continue evaluating semantic retrieval against a controlled
  question-and-evidence dataset.
- Measure exact-search latency before considering approximate indexing,
  such as pgvector HNSW.
- Add grounded answer generation and explicit handling of insufficient
  or conflicting evidence.

Query embedding is implemented through `EmbeddingGenerator.embed_query()`.
The retrieval service uses this method to embed user queries with the same
configured model used for passage embeddings. The caller remains responsible
for ensuring stored passage vectors and query vectors use compatible
embedding settings.

These capabilities belong to downstream retrieval and answer-generation
components; they are not responsibilities of `EmbeddingGenerator`.
