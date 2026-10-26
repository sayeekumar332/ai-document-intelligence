# Python Development and Verification Commands

This document records the commands used to configure, test, and verify the
AI Document Intelligence project, including embedding generation.

Run commands from the project root unless otherwise specified.

## 1. Activate the Python Environment

```bash
source .venv/bin/activate
python --version
```

The environment used for embedding-generation verification was Python 3.12.3.

## 2. Install Dependencies

```bash
python -m pip install -e ".[dev]"
python -m pip check
```

Expected output from a successful dependency check:

```text
No broken requirements found.
```

The project declares `sentence-transformers>=5.0,<6`.

## 3. Run Ruff

Check the entire project:

```bash
python -m ruff check .
```

Check a specific test file:

```bash
python -m ruff check tests/unit/test_embedding_generator.py
```

Apply automatic fixes where appropriate:

```bash
python -m ruff check --fix tests/unit/test_embedding_generator.py
```

Review automatic changes before committing them.

## 4. Run Embedding-Generator Unit Tests

```bash
python -m pytest tests/unit/test_embedding_generator.py -v
```

These tests use a mocked embedding model and cover provenance preservation,
input ordering, empty input, invalid configuration, invalid vector counts
and dimensions, non-finite values, model failures, immutable results, and
offline model-loading configuration.

## 5. Run the Real-Model Integration Test

```bash
python -m pytest tests/integration/test_embedding_generation.py -v
```

This test verifies inference using
`sentence-transformers/all-MiniLM-L6-v2`, including vector dimensions,
finite values, and passage provenance.

It checks the local model cache and skips if required files are unavailable.
It does not intentionally download model weights.

## 6. Run the Complete Test Suite

```bash
python -m pytest
```

For detailed test output:

```bash
python -m pytest -v
```

### Recorded verification result

For embedding-generation commit `1fae050` (`Add local embedding generation`):

- 41 tests passed.
- Five SWIG-related deprecation warnings were reported.
- No tests failed.

## 7. Run a Real-Model Smoke Test

Run this command with the virtual environment activated and the model
already available in the local cache:

```bash
python - <<'PY'
from math import isfinite

from ai_document_intelligence.embeddings.embedding_generator import (
    EmbeddingGenerator,
)
from ai_document_intelligence.ingestion.passage_chunker import Passage

passage = Passage(
    passage_id="smoke-test:p1:c0",
    document_id="smoke-test",
    source_name="smoke-test.pdf",
    page_number=1,
    text=(
        "A microprocessor executes instructions using its control "
        "unit and registers."
    ),
)

generator = EmbeddingGenerator(offline=True, device="cpu")
results = generator.generate([passage])

assert len(results) == 1
result = results[0]

assert result.passage_id == passage.passage_id
assert result.document_id == passage.document_id
assert result.source_name == passage.source_name
assert result.page_number == passage.page_number
assert len(result.embedding) == 384
assert all(isfinite(value) for value in result.embedding)

print("Passage ID:", result.passage_id)
print("Source:", result.source_name)
print("Page:", result.page_number)
print("Embedding dimensions:", len(result.embedding))
print("All values finite:", all(isfinite(v) for v in result.embedding))
print("REAL MODEL SMOKE TEST PASSED")
PY
```

Expected key result: 384 embedding dimensions, finite vector values, preserved
provenance, and `REAL MODEL SMOKE TEST PASSED`.

The `offline=True` setting requires locally cached model files and prevents
the model loader from fetching missing files during inference.

## 8. Recommended Verification Sequence

After changing Python code or dependencies:

```bash
python -m ruff check .
python -m pytest
python -m pip check
git diff --check
```

Check the working tree before committing:

```bash
git status --short
```

## 9. Model and Data Handling

- Keep model weights and Hugging Face caches outside version control.
- Do not commit private reference PDFs or generated embedding vectors.
- Keep virtual environments, Python bytecode, and generated caches out of Git.
- Use unit tests for fast, repeatable checks.
- Use the real-model integration test to verify cached-model inference.
- Use offline mode when network-independent inference is required.
