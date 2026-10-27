"""Integration tests for PostgreSQL-backed vector indexing."""

import os
from collections.abc import Iterator

import psycopg
import pytest

from ai_document_intelligence.embeddings.embedding_generator import (
    EmbeddedPassage,
)
from ai_document_intelligence.retrieval import (
    PostgresVectorIndex,
    SearchResult,
    VectorIndexError,
)

TEST_MODEL_NAME = "test-model/postgres-integration"
TEST_EMBEDDING_DIMENSION = 3


def make_passage(
    passage_id: str,
    embedding: tuple[float, ...],
    *,
    document_id: str = "doc-1",
    source_name: str = "reference.pdf",
    page_number: int = 1,
    text: str | None = None,
) -> EmbeddedPassage:
    """Build a minimal embedded passage for database tests."""
    return EmbeddedPassage(
        passage_id=passage_id,
        document_id=document_id,
        source_name=source_name,
        page_number=page_number,
        text=text or f"Test passage {passage_id}.",
        embedding=embedding,
    )


@pytest.fixture
def postgres_connection_params() -> dict[str, str | int]:
    """Read test database settings and ensure the database is reachable."""
    required_environment = (
        "POSTGRES_TEST_DB",
        "APP_DB_USER",
        "APP_DB_PASSWORD",
    )
    missing = [
        name for name in required_environment if not os.environ.get(name)
    ]
    if missing:
        pytest.skip(
            "PostgreSQL integration settings are unavailable. "
            "Load the local .env before running integration tests."
        )

    test_database = os.environ["POSTGRES_TEST_DB"]
    if test_database != "ai_document_intelligence_test":
        pytest.fail(
            "Refusing to run destructive integration tests unless "
            "POSTGRES_TEST_DB=ai_document_intelligence_test."
        )

    if test_database == os.environ.get("POSTGRES_DB"):
        pytest.fail(
            "The PostgreSQL test database must differ from the development database."
        )

    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail(
            "Refusing to run destructive integration tests against "
            "a non-loopback database host."
        )

    try:
        port = int(os.environ.get("POSTGRES_HOST_PORT", "54329"))
    except ValueError:
        pytest.fail("POSTGRES_HOST_PORT must be an integer.")

    params: dict[str, str | int] = {
        "host": host,
        "port": port,
        "dbname": os.environ["POSTGRES_TEST_DB"],
        "user": os.environ["APP_DB_USER"],
        "password": os.environ["APP_DB_PASSWORD"],
        "connect_timeout": 3,
        "application_name": "ai-document-intelligence-tests",
    }

    try:
        with psycopg.connect(**params) as connection:
            extension = connection.execute(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
                """
            ).fetchone()
    except psycopg.OperationalError as exc:
        if exc.sqlstate is None:
            pytest.skip(
                "PostgreSQL is not reachable; start the local Compose database."
            )
        pytest.fail(
            "PostgreSQL rejected the integration-test connection "
            f"(SQLSTATE {exc.sqlstate})."
        )

    if extension is None:
        pytest.fail(
            "The configured test database does not have the pgvector extension."
        )

    return params


@pytest.fixture
def vector_index(
    postgres_connection_params: dict[str, str | int],
) -> Iterator[PostgresVectorIndex]:
    """Provide a clean index connected only to the dedicated test database."""
    index = PostgresVectorIndex(
        connection_params=postgres_connection_params,
        model_name=TEST_MODEL_NAME,
        embedding_dimension=TEST_EMBEDDING_DIMENSION,
    )

    # This fixture is only configured to use POSTGRES_TEST_DB.
    with psycopg.connect(**postgres_connection_params) as connection:
        connection.execute("DELETE FROM public.passages")

    try:
        yield index
    finally:
        with psycopg.connect(**postgres_connection_params) as connection:
            connection.execute("DELETE FROM public.passages")


def test_empty_index_returns_no_results(
    vector_index: PostgresVectorIndex,
) -> None:
    assert vector_index.count() == 0
    assert vector_index.search((1.0, 0.0, 0.0)) == []


def test_upsert_preserves_provenance_and_persists_across_reopen(
    vector_index: PostgresVectorIndex,
    postgres_connection_params: dict[str, str | int],
) -> None:
    passage = make_passage(
        "doc-1:p2:c0",
        (1.0, 0.0, 0.0),
        document_id="doc-1",
        source_name="manual.pdf",
        page_number=2,
        text="The control unit coordinates instruction execution.",
    )

    vector_index.upsert([passage])

    reopened = PostgresVectorIndex(
        connection_params=postgres_connection_params,
        model_name=TEST_MODEL_NAME,
        embedding_dimension=TEST_EMBEDDING_DIMENSION,
    )

    assert reopened.count() == 1
    results = reopened.search((1.0, 0.0, 0.0), top_k=1)

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, SearchResult)
    assert result.passage_id == passage.passage_id
    assert result.document_id == passage.document_id
    assert result.source_name == passage.source_name
    assert result.page_number == passage.page_number
    assert result.text == passage.text
    assert result.score == pytest.approx(1.0)


def test_cosine_ranking_and_tie_breaking_are_deterministic(
    vector_index: PostgresVectorIndex,
) -> None:
    vector_index.upsert(
        [
            make_passage("p-z", (1.0, 0.0, 0.0)),
            make_passage("p-a", (1.0, 0.0, 0.0)),
            make_passage("p-orthogonal", (0.0, 1.0, 0.0)),
            make_passage("p-opposite", (-1.0, 0.0, 0.0)),
        ]
    )

    results = vector_index.search((1.0, 0.0, 0.0), top_k=4)

    assert [result.passage_id for result in results] == [
        "p-a",
        "p-z",
        "p-orthogonal",
        "p-opposite",
    ]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(1.0)
    assert results[2].score == pytest.approx(0.0)
    assert results[3].score == pytest.approx(-1.0)


def test_upsert_updates_an_existing_passage(
    vector_index: PostgresVectorIndex,
) -> None:
    vector_index.upsert(
        [
            make_passage(
                "same-id",
                (1.0, 0.0, 0.0),
                text="Original passage.",
            )
        ]
    )
    vector_index.upsert(
        [
            make_passage(
                "same-id",
                (0.0, 1.0, 0.0),
                document_id="updated-document",
                source_name="updated.pdf",
                page_number=3,
                text="Updated passage.",
            )
        ]
    )

    assert vector_index.count() == 1
    result = vector_index.search((0.0, 1.0, 0.0), top_k=1)[0]
    assert result.document_id == "updated-document"
    assert result.source_name == "updated.pdf"
    assert result.page_number == 3
    assert result.text == "Updated passage."
    assert result.score == pytest.approx(1.0)


def test_delete_document_only_removes_that_documents_passages(
    vector_index: PostgresVectorIndex,
) -> None:
    vector_index.upsert(
        [
            make_passage("doc-a-1", (1.0, 0.0, 0.0), document_id="doc-a"),
            make_passage("doc-a-2", (0.0, 1.0, 0.0), document_id="doc-a"),
            make_passage("doc-b-1", (0.0, 0.0, 1.0), document_id="doc-b"),
        ]
    )

    assert vector_index.delete_document("doc-a") == 2
    assert vector_index.count() == 1
    assert vector_index.delete_document("doc-a") == 0
    assert vector_index.search((0.0, 0.0, 1.0), top_k=1)[0].passage_id == (
        "doc-b-1"
    )



def test_search_can_be_scoped_to_one_document(
    vector_index: PostgresVectorIndex,
) -> None:
    vector_index.upsert(
        [
            make_passage(
                "doc-a-match",
                (0.8, 0.6, 0.0),
                document_id="doc-a",
                text="Passage from document A.",
            ),
            make_passage(
                "doc-b-best-global-match",
                (1.0, 0.0, 0.0),
                document_id="doc-b",
                text="Passage from document B.",
            ),
            make_passage(
                "doc-a-second",
                (0.0, 1.0, 0.0),
                document_id="doc-a",
                text="Another passage from document A.",
            ),
        ]
    )

    global_results = vector_index.search((1.0, 0.0, 0.0), top_k=3)
    assert global_results[0].passage_id == "doc-b-best-global-match"

    scoped_results = vector_index.search(
        (1.0, 0.0, 0.0),
        top_k=3,
        document_id="doc-a",
    )
    assert scoped_results
    assert all(result.document_id == "doc-a" for result in scoped_results)
    assert {result.passage_id for result in scoped_results} == {
        "doc-a-match",
        "doc-a-second",
    }


@pytest.mark.parametrize("document_id", ["", "  ", "\n", 123, False])
def test_search_rejects_invalid_document_id(
    vector_index: PostgresVectorIndex,
    document_id: object,
) -> None:
    with pytest.raises(
        VectorIndexError,
        match="document_id must be a non-empty string",
    ):
        vector_index.search(
            (1.0, 0.0, 0.0),
            document_id=document_id,  # type: ignore[arg-type]
        )


def test_invalid_query_parameters_are_rejected(
    vector_index: PostgresVectorIndex,
) -> None:
    with pytest.raises(VectorIndexError, match="top_k"):
        vector_index.search((1.0, 0.0, 0.0), top_k=0)

    with pytest.raises(VectorIndexError, match="dimension"):
        vector_index.search((1.0, 0.0), top_k=1)

    with pytest.raises(VectorIndexError, match="non-finite"):
        vector_index.search((float("nan"), 0.0, 1.0))

    with pytest.raises(VectorIndexError, match="non-zero norm"):
        vector_index.search((0.0, 0.0, 0.0))


def test_invalid_batch_is_rejected_before_writing(
    vector_index: PostgresVectorIndex,
) -> None:
    valid = make_passage("valid-first", (1.0, 0.0, 0.0))
    invalid = make_passage("invalid-second", (1.0, 0.0))

    with pytest.raises(VectorIndexError, match="dimension"):
        vector_index.upsert([valid, invalid])

    assert vector_index.count() == 0


def test_duplicate_ids_in_batch_are_rejected(
    vector_index: PostgresVectorIndex,
) -> None:
    with pytest.raises(VectorIndexError, match="Duplicate passage_id"):
        vector_index.upsert(
            [
                make_passage("duplicate", (1.0, 0.0, 0.0)),
                make_passage("duplicate", (0.0, 1.0, 0.0)),
            ]
        )

    assert vector_index.count() == 0


def test_model_mismatch_is_rejected(
    vector_index: PostgresVectorIndex,
    postgres_connection_params: dict[str, str | int],
) -> None:
    with pytest.raises(VectorIndexError, match="model_name"):
        PostgresVectorIndex(
            connection_params=postgres_connection_params,
            model_name="different-test-model",
            embedding_dimension=TEST_EMBEDDING_DIMENSION,
        )


def test_database_failure_rolls_back_the_entire_batch(
    vector_index: PostgresVectorIndex,
    postgres_connection_params: dict[str, str | int],
) -> None:
    """Use a temporary trigger to force a real transactional write failure."""
    trigger_name = "test_vector_index_force_failure"
    function_name = "test_vector_index_force_failure_fn"

    with psycopg.connect(**postgres_connection_params) as connection:
        with connection.transaction():
            connection.execute(
                f"DROP TRIGGER IF EXISTS {trigger_name} ON public.passages"
            )
            connection.execute(
                f"DROP FUNCTION IF EXISTS public.{function_name}()"
            )
            connection.execute(
                f"""
                CREATE FUNCTION public.{function_name}()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $test$
                BEGIN
                    IF NEW.passage_id = 'forced-failure' THEN
                        RAISE EXCEPTION 'forced failure for integration test';
                    END IF;
                    RETURN NEW;
                END;
                $test$;
                """
            )
            connection.execute(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE INSERT OR UPDATE ON public.passages
                FOR EACH ROW
                EXECUTE FUNCTION public.{function_name}()
                """
            )

    try:
        with pytest.raises(VectorIndexError, match="PostgreSQL operation failed"):
            vector_index.upsert(
                [
                    make_passage("would-be-first", (1.0, 0.0, 0.0)),
                    make_passage("forced-failure", (0.0, 1.0, 0.0)),
                ]
            )

        assert vector_index.count() == 0
    finally:
        with psycopg.connect(**postgres_connection_params) as connection:
            with connection.transaction():
                connection.execute(
                    f"DROP TRIGGER IF EXISTS {trigger_name} ON public.passages"
                )
                connection.execute(
                    f"DROP FUNCTION IF EXISTS public.{function_name}()"
                )
