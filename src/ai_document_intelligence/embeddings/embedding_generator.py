"""Generate local, provenance-preserving text embeddings."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from ai_document_intelligence.ingestion.passage_chunker import Passage

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384


class EmbeddingGenerationError(RuntimeError):
    """Raised when embeddings cannot be generated or validated."""


class EmbeddingModel(Protocol):
    """Minimal interface required from an embedding model."""

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> object:
        """Encode a batch of texts."""


@dataclass(frozen=True)
class EmbeddedPassage:
    """A passage and its embedding, retaining its original provenance."""

    passage_id: str
    document_id: str
    source_name: str
    page_number: int
    text: str
    embedding: tuple[float, ...]


class EmbeddingGenerator:
    """Generate embeddings with a lazily loaded Sentence Transformers model."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        *,
        device: str | None = None,
        expected_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
        batch_size: int = 32,
        model: EmbeddingModel | None = None,
        offline: bool = False,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty.")
        if expected_dimension <= 0:
            raise ValueError("expected_dimension must be greater than zero.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self.model_name = model_name
        self.device = device
        self.expected_dimension = expected_dimension
        self.batch_size = batch_size
        self._model = model
        self.offline = offline

    def _get_model(self) -> EmbeddingModel:
        """Load the model only when a non-empty batch needs encoding."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    local_files_only=self.offline,
                )
            except Exception as exc:
                raise EmbeddingGenerationError(
                    f"Could not load embedding model {self.model_name!r}: {exc}"
                ) from exc

        return self._model

    def generate(
        self,
        passages: Sequence[Passage],
    ) -> list[EmbeddedPassage]:
        """Embed passages and preserve their order and provenance."""
        if not passages:
            return []

        for passage in passages:
            if not passage.text.strip():
                raise EmbeddingGenerationError(
                    f"Passage {passage.passage_id!r} contains no usable text."
                )

        model = self._get_model()

        try:
            vectors = model.encode(
                [passage.text for passage in passages],
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingGenerationError(
                f"Embedding generation failed using {self.model_name!r}: {exc}"
            ) from exc

        try:
            rows = list(vectors)
        except (TypeError, ValueError) as exc:
            raise EmbeddingGenerationError(
                "The embedding model returned an invalid result."
            ) from exc

        if len(rows) != len(passages):
            raise EmbeddingGenerationError(
                f"Expected {len(passages)} embedding vectors, received {len(rows)}."
            )

        results: list[EmbeddedPassage] = []

        for passage, row in zip(passages, rows, strict=True):
            try:
                vector = tuple(float(value) for value in row)
            except (TypeError, ValueError, OverflowError) as exc:
                raise EmbeddingGenerationError(
                    f"Invalid embedding vector for passage {passage.passage_id!r}."
                ) from exc

            if len(vector) != self.expected_dimension:
                raise EmbeddingGenerationError(
                    f"Passage {passage.passage_id!r} has embedding dimension "
                    f"{len(vector)}; expected {self.expected_dimension}."
                )

            if not all(isfinite(value) for value in vector):
                raise EmbeddingGenerationError(
                    f"Embedding for passage {passage.passage_id!r} "
                    "contains a non-finite value."
                )

            results.append(
                EmbeddedPassage(
                    passage_id=passage.passage_id,
                    document_id=passage.document_id,
                    source_name=passage.source_name,
                    page_number=passage.page_number,
                    text=passage.text,
                    embedding=vector,
                )
            )

        return results
