"""Integration tests for the real, locally cached embedding model."""

from math import isfinite

import pytest
from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError

from ai_document_intelligence.embeddings.embedding_generator import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_MODEL_NAME,
    EmbeddingGenerator,
)
from ai_document_intelligence.ingestion.passage_chunker import Passage


def test_real_embedding_model_generates_valid_embeddings_offline() -> None:
    """Verify real model inference without requiring network access."""
    try:
        snapshot_download(
            repo_id=DEFAULT_MODEL_NAME,
            local_files_only=True,
        )
    except LocalEntryNotFoundError:
        pytest.skip("Embedding model is not fully available in the local cache.")

    passage = Passage(
        passage_id="integration-test:p1:c0",
        document_id="integration-test",
        source_name="integration-test.pdf",
        page_number=1,
        text=(
            "A microprocessor executes instructions using its control "
            "unit and registers."
        ),
    )

    generator = EmbeddingGenerator(offline=True, device="cpu")
    results = generator.generate([passage])

    assert len(results) == 1

    embedded = results[0]
    assert embedded.passage_id == passage.passage_id
    assert embedded.document_id == passage.document_id
    assert embedded.source_name == passage.source_name
    assert embedded.page_number == passage.page_number
    assert embedded.text == passage.text

    assert len(embedded.embedding) == DEFAULT_EMBEDDING_DIMENSION
    assert all(isfinite(value) for value in embedded.embedding)
