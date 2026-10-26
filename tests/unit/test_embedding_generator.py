"""Unit tests for provenance-preserving embedding generation."""

from dataclasses import FrozenInstanceError

import pytest

from ai_document_intelligence.embeddings.embedding_generator import (
    DEFAULT_MODEL_NAME,
    EmbeddedPassage,
    EmbeddingGenerationError,
    EmbeddingGenerator,
)
from ai_document_intelligence.ingestion.passage_chunker import Passage


class FakeEmbeddingModel:
    """Deterministic model substitute for unit tests."""

    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[dict[str, object]] = []

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        self.calls.append(
            {
                "sentences": sentences,
                "batch_size": batch_size,
                "convert_to_numpy": convert_to_numpy,
                "normalize_embeddings": normalize_embeddings,
                "show_progress_bar": show_progress_bar,
            }
        )
        return self.vectors


def make_passage(
    passage_id: str = "doc-1:p1:c0",
    text: str = "Example technical passage.",
) -> Passage:
    return Passage(
        passage_id=passage_id,
        document_id="doc-1",
        source_name="reference.pdf",
        page_number=1,
        text=text,
    )


def test_generate_preserves_provenance_and_embedding() -> None:
    passage = make_passage()
    model = FakeEmbeddingModel([[0.6, 0.8]])
    generator = EmbeddingGenerator(
        model=model,
        expected_dimension=2,
    )

    results = generator.generate([passage])

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, EmbeddedPassage)
    assert result.passage_id == passage.passage_id
    assert result.document_id == passage.document_id
    assert result.source_name == passage.source_name
    assert result.page_number == passage.page_number
    assert result.text == passage.text
    assert result.embedding == (0.6, 0.8)

    assert model.calls[0]["sentences"] == [passage.text]
    assert model.calls[0]["normalize_embeddings"] is True
    assert model.calls[0]["show_progress_bar"] is False


def test_generate_preserves_input_order() -> None:
    passages = [
        make_passage("doc-1:p1:c0", "First passage."),
        make_passage("doc-1:p2:c0", "Second passage."),
    ]
    model = FakeEmbeddingModel([[1.0, 0.0], [0.0, 1.0]])
    generator = EmbeddingGenerator(model=model, expected_dimension=2)

    results = generator.generate(passages)

    assert [result.passage_id for result in results] == [
        "doc-1:p1:c0",
        "doc-1:p2:c0",
    ]


def test_empty_input_does_not_call_model() -> None:
    model = FakeEmbeddingModel([])
    generator = EmbeddingGenerator(model=model, expected_dimension=2)

    assert generator.generate([]) == []
    assert model.calls == []


def test_whitespace_only_passage_is_rejected() -> None:
    model = FakeEmbeddingModel([])
    generator = EmbeddingGenerator(model=model, expected_dimension=2)

    with pytest.raises(EmbeddingGenerationError, match="no usable text"):
        generator.generate([make_passage(text="  \n\t")])

    assert model.calls == []


def test_wrong_number_of_vectors_is_rejected() -> None:
    model = FakeEmbeddingModel([[1.0, 0.0]])
    generator = EmbeddingGenerator(model=model, expected_dimension=2)

    with pytest.raises(EmbeddingGenerationError, match="Expected 2"):
        generator.generate(
            [
                make_passage("doc-1:p1:c0", "First."),
                make_passage("doc-1:p1:c1", "Second."),
            ]
        )


def test_wrong_embedding_dimension_is_rejected() -> None:
    model = FakeEmbeddingModel([[1.0, 0.0, 0.5]])
    generator = EmbeddingGenerator(model=model, expected_dimension=2)

    with pytest.raises(EmbeddingGenerationError, match="expected 2"):
        generator.generate([make_passage()])


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_embedding_values_are_rejected(
    bad_value: float,
) -> None:
    model = FakeEmbeddingModel([[bad_value, 0.0]])
    generator = EmbeddingGenerator(model=model, expected_dimension=2)

    with pytest.raises(EmbeddingGenerationError, match="non-finite"):
        generator.generate([make_passage()])


def test_model_failure_is_wrapped() -> None:
    class FailingModel:
        def encode(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("simulated backend failure")

    generator = EmbeddingGenerator(
        model=FailingModel(),  # type: ignore[arg-type]
        expected_dimension=2,
    )

    with pytest.raises(EmbeddingGenerationError, match="generation failed"):
        generator.generate([make_passage()])


def test_embedded_passage_is_immutable() -> None:
    result = EmbeddedPassage(
        passage_id="doc-1:p1:c0",
        document_id="doc-1",
        source_name="reference.pdf",
        page_number=1,
        text="Example.",
        embedding=(1.0, 0.0),
    )

    with pytest.raises(FrozenInstanceError):
        result.text = "Changed."  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"batch_size": 0}, "batch_size"),
        ({"expected_dimension": 0}, "expected_dimension"),
        ({"model_name": " "}, "model_name"),
    ],
)
def test_invalid_configuration_is_rejected(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        EmbeddingGenerator(**kwargs)  # type: ignore[arg-type]

def test_offline_setting_is_preserved() -> None:
    model = FakeEmbeddingModel([[0.6, 0.8]])
    generator = EmbeddingGenerator(
        model=model,
        expected_dimension=2,
        offline=True,
    )

    assert generator.offline is True
    assert generator.generate([make_passage()])[0].embedding == (0.6, 0.8)

def test_offline_mode_is_forwarded_to_model_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    from types import ModuleType
    from unittest.mock import Mock

    fake_model = Mock()
    constructor = Mock(return_value=fake_model)

    fake_module = ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = constructor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    generator = EmbeddingGenerator(offline=True)
    loaded_model = generator._get_model()

    assert loaded_model is fake_model
    constructor.assert_called_once_with(
        DEFAULT_MODEL_NAME,
        device=None,
        local_files_only=True,
    )