"""PostgreSQL persistence and exact cosine-similarity search with pgvector."""

import os
import struct
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from math import hypot, isfinite

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from ai_document_intelligence.embeddings.embedding_generator import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_MODEL_NAME,
    EmbeddedPassage,
)

SCHEMA_VERSION = "1"
VECTOR_ENCODING = "pgvector-vector"
DISTANCE_METRIC = "cosine"
APPLICATION_NAME = "ai-document-intelligence"


class VectorIndexError(RuntimeError):
    """Raised when PostgreSQL index operations or validation fail."""


@dataclass(frozen=True)
class SearchResult:
    """A ranked passage with its original provenance and similarity score."""

    passage_id: str
    document_id: str
    source_name: str
    page_number: int
    text: str
    score: float


class PostgresVectorIndex:
    """Persist embedded passages and search them using PostgreSQL and pgvector.

    If connection parameters are not explicitly provided, the index reads:
    POSTGRES_HOST, POSTGRES_HOST_PORT, POSTGRES_DB, APP_DB_USER, and
    APP_DB_PASSWORD from the process environment.

    The caller must ensure that stored passages and query embeddings were
    generated using the configured model and compatible embedding settings.
    """

    def __init__(
        self,
        *,
        connection_params: Mapping[str, str | int] | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must not be empty.")

        if (
            isinstance(embedding_dimension, bool)
            or not isinstance(embedding_dimension, int)
            or embedding_dimension <= 0
        ):
            raise ValueError("embedding_dimension must be a positive integer.")

        self.model_name = model_name
        self.embedding_dimension = embedding_dimension
        self._connection_params = self._make_connection_params(connection_params)

        self._initialize()

    @staticmethod
    def _make_connection_params(
        connection_params: Mapping[str, str | int] | None,
    ) -> dict[str, str | int]:
        """Build connection settings without embedding credentials in source."""
        if connection_params is None:
            raw_port = os.environ.get("POSTGRES_HOST_PORT", "54329")
            try:
                port = int(raw_port)
            except ValueError as exc:
                raise ValueError(
                    "POSTGRES_HOST_PORT must be an integer."
                ) from exc

            params: dict[str, str | int] = {
                "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
                "port": port,
                "dbname": os.environ.get(
                    "POSTGRES_DB", "ai_document_intelligence"
                ),
                "user": os.environ.get("APP_DB_USER", "ai_document_app"),
                "password": os.environ.get("APP_DB_PASSWORD", ""),
            }
        else:
            params = dict(connection_params)

        if not params.get("password"):
            raise ValueError(
                "Database password is not configured. Provide connection_params "
                "or load APP_DB_PASSWORD into the environment."
            )

        for required in ("host", "port", "dbname", "user"):
            if not params.get(required):
                raise ValueError(
                    f"Database connection parameter {required!r} is required."
                )

        params.setdefault("connect_timeout", 5)
        params.setdefault("application_name", APPLICATION_NAME)
        return params

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection]:
        """Open a connection, register pgvector, and manage its transaction."""
        try:
            with psycopg.connect(**self._connection_params) as connection:
                register_vector(connection)
                yield connection
        except VectorIndexError:
            raise
        except psycopg.Error as exc:
            # Avoid including connection parameters or credentials in messages.
            raise VectorIndexError(
                "PostgreSQL operation failed. Check database availability, "
                "credentials, schema permissions, and pgvector installation."
            ) from exc

    def _initialize(self) -> None:
        """Create the schema once and validate existing index metadata."""
        with self._connection() as connection:
            extension_row = connection.execute(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
                """
            ).fetchone()

            if extension_row is None:
                raise VectorIndexError(
                    "The pgvector extension is not installed in this database."
                )

            pgvector_version = str(extension_row[0])

            with connection.transaction():
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.index_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                    """
                )

                metadata_rows = connection.execute(
                    "SELECT key, value FROM public.index_metadata"
                ).fetchall()
                actual = {str(row[0]): str(row[1]) for row in metadata_rows}

                if not actual:
                    existing_table = connection.execute(
                        "SELECT to_regclass('public.passages')"
                    ).fetchone()[0]

                    if existing_table is not None:
                        raise VectorIndexError(
                            "The passages table exists without index metadata; "
                            "refusing to assume its configuration."
                        )

                    connection.execute(
                        f"""
                        CREATE TABLE public.passages (
                            passage_id TEXT PRIMARY KEY,
                            document_id TEXT NOT NULL,
                            source_name TEXT NOT NULL,
                            page_number INTEGER NOT NULL
                                CHECK (page_number > 0),
                            text TEXT NOT NULL,
                            embedding public.vector(
                                {self.embedding_dimension}
                            ) NOT NULL
                        )
                        """
                    )

                    connection.execute(
                        """
                        CREATE INDEX idx_passages_document_id
                        ON public.passages(document_id)
                        """
                    )

                    initial_metadata = {
                        "schema_version": SCHEMA_VERSION,
                        "model_name": self.model_name,
                        "embedding_dimension": str(self.embedding_dimension),
                        "vector_encoding": VECTOR_ENCODING,
                        "distance_metric": DISTANCE_METRIC,
                        "pgvector_version": pgvector_version,
                    }
                    with connection.cursor() as cursor:
                        cursor.executemany(
                            """
                            INSERT INTO public.index_metadata (key, value)
                            VALUES (%s, %s)
                            """,
                            list(initial_metadata.items()),
                        )
                    return

                expected = {
                    "schema_version": SCHEMA_VERSION,
                    "model_name": self.model_name,
                    "embedding_dimension": str(self.embedding_dimension),
                    "vector_encoding": VECTOR_ENCODING,
                    "distance_metric": DISTANCE_METRIC,
                }

                for key, expected_value in expected.items():
                    actual_value = actual.get(key)
                    if actual_value != expected_value:
                        raise VectorIndexError(
                            f"Incompatible index metadata for {key!r}: "
                            f"stored {actual_value!r}, "
                            f"requested {expected_value!r}."
                        )

                if "pgvector_version" not in actual:
                    raise VectorIndexError(
                        "The index metadata is missing pgvector_version."
                    )

                table_row = connection.execute(
                    "SELECT to_regclass('public.passages')"
                ).fetchone()
                if table_row[0] is None:
                    raise VectorIndexError(
                        "Index metadata exists, but public.passages is missing."
                    )

                column_row = connection.execute(
                    """
                    SELECT format_type(atttypid, atttypmod)
                    FROM pg_attribute
                    WHERE attrelid = 'public.passages'::regclass
                      AND attname = 'embedding'
                      AND NOT attisdropped
                    """
                ).fetchone()

                expected_type = f"vector({self.embedding_dimension})"
                if column_row is None or column_row[0] != expected_type:
                    stored_type = None if column_row is None else column_row[0]
                    raise VectorIndexError(
                        "Incompatible embedding column type: "
                        f"stored {stored_type!r}, expected {expected_type!r}."
                    )

    def _validate_vector(
        self,
        vector: Sequence[float],
        *,
        label: str,
    ) -> tuple[float, ...]:
        """Validate, round to float32 precision, and check the vector norm."""
        if isinstance(vector, (str, bytes, bytearray)):
            raise VectorIndexError(f"{label} must be a numerical sequence.")

        try:
            values = tuple(float(value) for value in vector)
        except (TypeError, ValueError, OverflowError) as exc:
            raise VectorIndexError(f"{label} contains a non-numeric value.") from exc

        if len(values) != self.embedding_dimension:
            raise VectorIndexError(
                f"{label} has dimension {len(values)}; expected "
                f"{self.embedding_dimension}."
            )

        if not all(isfinite(value) for value in values):
            raise VectorIndexError(f"{label} contains a non-finite value.")

        try:
            packed = struct.pack(f"<{self.embedding_dimension}f", *values)
            float32_values = struct.unpack(
                f"<{self.embedding_dimension}f", packed
            )
        except (OverflowError, struct.error) as exc:
            raise VectorIndexError(
                f"{label} contains a value that cannot be represented as float32."
            ) from exc

        if not all(isfinite(value) for value in float32_values):
            raise VectorIndexError(
                f"{label} contains a value that becomes non-finite as float32."
            )

        if hypot(*float32_values) == 0.0:
            raise VectorIndexError(f"{label} must have a non-zero norm.")

        return float32_values

    @staticmethod
    def _validate_text(value: str, *, field_name: str, passage_id: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise VectorIndexError(
                f"Passage {passage_id!r} has an empty or invalid {field_name}."
            )

    def upsert(self, passages: Sequence[EmbeddedPassage]) -> None:
        """Insert or update passages in one transaction."""
        items = list(passages)
        if not items:
            return

        records: list[tuple[str, str, str, int, str, Vector]] = []
        seen_ids: set[str] = set()

        # Validate the full batch before opening a write transaction.
        for passage in items:
            if not isinstance(passage, EmbeddedPassage):
                raise VectorIndexError(
                    "upsert expects EmbeddedPassage objects."
                )

            passage_id = passage.passage_id
            if not isinstance(passage_id, str) or not passage_id.strip():
                raise VectorIndexError("passage_id must not be empty.")

            if passage_id in seen_ids:
                raise VectorIndexError(
                    f"Duplicate passage_id {passage_id!r} in upsert batch."
                )
            seen_ids.add(passage_id)

            self._validate_text(
                passage.document_id,
                field_name="document_id",
                passage_id=passage_id,
            )
            self._validate_text(
                passage.source_name,
                field_name="source_name",
                passage_id=passage_id,
            )
            self._validate_text(
                passage.text,
                field_name="text",
                passage_id=passage_id,
            )

            if (
                isinstance(passage.page_number, bool)
                or not isinstance(passage.page_number, int)
                or passage.page_number <= 0
            ):
                raise VectorIndexError(
                    f"Passage {passage_id!r} must have a positive page number."
                )

            values = self._validate_vector(
                passage.embedding,
                label=f"Embedding for passage {passage_id!r}",
            )

            records.append(
                (
                    passage_id,
                    passage.document_id,
                    passage.source_name,
                    passage.page_number,
                    passage.text,
                    Vector(list(values)),
                )
            )

        with self._connection() as connection:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.executemany(
                        """
                        INSERT INTO public.passages (
                            passage_id,
                            document_id,
                            source_name,
                            page_number,
                            text,
                            embedding
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (passage_id) DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            source_name = EXCLUDED.source_name,
                            page_number = EXCLUDED.page_number,
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding
                        """,
                        records,
                    )

    def delete_document(self, document_id: str) -> int:
        """Delete a document's passages and return the number deleted."""
        if not isinstance(document_id, str) or not document_id.strip():
            raise VectorIndexError("document_id must not be empty.")

        with self._connection() as connection:
            with connection.transaction():
                cursor = connection.execute(
                    """
                    DELETE FROM public.passages
                    WHERE document_id = %s
                    """,
                    (document_id,),
                )
                return cursor.rowcount

    def search(
        self,
        query_embedding: Sequence[float],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        """Return cosine-ranked passages, optionally scoped to a document."""
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            raise VectorIndexError("top_k must be a positive integer.")

        if document_id is not None and (
            not isinstance(document_id, str) or not document_id.strip()
        ):
            raise VectorIndexError(
                "document_id must be a non-empty string when provided."
            )

        values = self._validate_vector(
            query_embedding,
            label="Query embedding",
        )
        query_vector = Vector(list(values))

        with self._connection() as connection:
            sql = """
                SELECT
                    passage_id,
                    document_id,
                    source_name,
                    page_number,
                    text,
                    1 - (embedding <=> %s) AS score
                FROM public.passages
            """
            if document_id is None:
                sql += """
                    ORDER BY embedding <=> %s, passage_id
                    LIMIT %s
                """
                parameters = (query_vector, query_vector, top_k)
            else:
                sql += """
                    WHERE document_id = %s
                    ORDER BY embedding <=> %s, passage_id
                    LIMIT %s
                """
                parameters = (
                    query_vector,
                    document_id,
                    query_vector,
                    top_k,
                )

            rows = connection.execute(sql, parameters).fetchall()

        return [
            SearchResult(
                passage_id=row[0],
                document_id=row[1],
                source_name=row[2],
                page_number=row[3],
                text=row[4],
                score=max(-1.0, min(1.0, float(row[5]))),
            )
            for row in rows
        ]

    def count(self) -> int:
        """Return the number of passages stored in the index."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM public.passages"
            ).fetchone()
            return int(row[0])
