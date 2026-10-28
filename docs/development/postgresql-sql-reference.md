# PostgreSQL and pgvector SQL Reference

This reference records the PostgreSQL commands and SQL patterns used by the
AI Document Intelligence project. It covers local connections, schema
inspection, index metadata, passage diagnostics, and the SQL operations used
by `PostgresVectorIndex`.

## 1. Environment at a glance

The current local Compose configuration uses:

- PostgreSQL 17 image: `pgvector/pgvector:0.8.7-pg17-bookworm`.
- pgvector extension, with the extension version recorded in database metadata.
- Default database: `ai_document_intelligence`.
- Default host binding: `127.0.0.1:54329`.
- Application role: configured by `APP_DB_USER` (example default: `ai_document_app`).
- Separate integration-test database: `ai_document_intelligence_test`.

Use the values from your own `.env` file as the source of truth. Never
paste passwords into commands, commit `.env`, or include credentials in logs.
The application should connect using the application role, not the
administrator role.

## 2. Open a psql session

From the repository root, open a session as the Compose administrator:

```bash
docker compose exec db sh -lc \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

For routine application-level inspection, connect as the application role:

```bash
docker compose exec db sh -lc \
  'PGPASSWORD="$APP_DB_PASSWORD" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB"'
```

The second command passes the password through the container environment
without printing its value as a command argument. Exit an interactive
`psql` session with:

```sql
\q
```

## 3. Confirm connection and extension

Show the server, database, and active role:

```sql
SELECT version();
SELECT current_database(), current_user, current_schema();
SHOW server_version;
```

Confirm that pgvector is installed in the database to which you are connected:

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

List installed extensions with the psql meta-command:

```text
\dx
\dx vector
```

An extension is installed per database. A successful check in the development
database does not prove that it is installed in the test database.

## 4. Inspect tables, columns, indexes, and constraints

In `psql`, these meta-commands are convenient for schema inspection:

```text
\dt public.*
\d+ public.passages
\d+ public.index_metadata
\di+ public.*
```

Equivalent catalog queries for use in SQL scripts:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

```sql
SELECT
    column_name,
    data_type,
    udt_name,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'passages'
ORDER BY ordinal_position;
```

List indexes attached to the passages table:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'passages'
ORDER BY indexname;
```

The index implementation creates these tables when the database has no
existing index metadata and no pre-existing `public.passages` table:

- `public.passages`: `passage_id`, `document_id`, `source_name`,
  `page_number`, `text`, and `embedding`.
- `public.index_metadata`: `key` and `value`.

The passage table uses a configurable `vector(n)` embedding column (384
dimensions with the initial model) and a B-tree index on `document_id`.
The metadata key is the primary key. The application refuses to assume the
configuration of a pre-existing passages table if its metadata is absent.

**Do not manually recreate or alter these tables in normal development.**
The `PostgresVectorIndex` constructor initializes and validates the schema.

## 5. Read the embedding-index metadata

Show the model and schema configuration recorded by the adapter:

```sql
SELECT key, value
FROM public.index_metadata
ORDER BY key;
```

Read selected configuration values in one row:

```sql
SELECT
    max(value) FILTER (WHERE key = 'schema_version') AS schema_version,
    max(value) FILTER (WHERE key = 'model_name') AS model_name,
    max(value) FILTER (WHERE key = 'embedding_dimension') AS embedding_dimension,
    max(value) FILTER (WHERE key = 'vector_encoding') AS vector_encoding,
    max(value) FILTER (WHERE key = 'distance_metric') AS distance_metric,
    max(value) FILTER (WHERE key = 'pgvector_version') AS pgvector_version
FROM public.index_metadata;
```

The expected default embedding model is
`sentence-transformers/all-MiniLM-L6-v2`, with 384 dimensions. The metadata
also records schema version, vector encoding, distance metric, and the
pgvector extension version observed when the index is initialized. A matching
dimension alone does not prove that every stored vector came from the
intended model; the caller must maintain embedding-space compatibility.

## 6. Inspect passages without dumping entire documents

Count all indexed passages:

```sql
SELECT COUNT(*) AS passage_count
FROM public.passages;
```

Count passages and distinct source documents:

```sql
SELECT
    COUNT(*) AS passage_count,
    COUNT(DISTINCT document_id) AS document_count
FROM public.passages;
```

Summarize passage counts by document:

```sql
SELECT
    document_id,
    source_name,
    COUNT(*) AS passage_count,
    MIN(page_number) AS first_page,
    MAX(page_number) AS last_page
FROM public.passages
GROUP BY document_id, source_name
ORDER BY source_name, document_id;
```

Inspect selected passage metadata and only a short text preview. This may
still reveal document content, so run it only on data you are authorized to view.

```sql
SELECT
    passage_id,
    document_id,
    source_name,
    page_number,
    LEFT(text, 160) AS text_preview
FROM public.passages
ORDER BY document_id, page_number, passage_id
LIMIT 20;
```

Look up a document using a known document ID:

```sql
SELECT passage_id, source_name, page_number, LENGTH(text) AS text_length
FROM public.passages
WHERE document_id = 'replace-with-a-known-document-id'
ORDER BY page_number, passage_id;
```

Replace the sample value with an actual document ID. For application code,
use a bound parameter rather than constructing SQL with string concatenation.

## 7. SQL patterns used by the Python adapter

These statements describe the SQL executed by
`src/ai_document_intelligence/retrieval/postgres_vector_index.py`.
The `%s` markers below are **Psycopg parameter placeholders**. These are
application SQL patterns, not statements to paste unchanged into an interactive
`psql` session.

### 7.1 Initialize index metadata table

```sql
CREATE TABLE IF NOT EXISTS public.index_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 7.2 Create passages table and document index

The dimension is interpolated only from the validated integer
configuration—not from user-controlled text.

```sql
CREATE TABLE public.passages (
    passage_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    text TEXT NOT NULL,
    embedding public.vector(384) NOT NULL
);

CREATE INDEX idx_passages_document_id
ON public.passages(document_id);
```

The example shows the initial 384-dimension configuration. The adapter
uses the configured dimension when creating a fresh index; do not run this
DDL manually against an existing database.

### 7.3 Store initialization metadata

The adapter inserts key/value pairs for `schema_version`, `model_name`,
`embedding_dimension`, `vector_encoding`, `distance_metric`, and
`pgvector_version` using a parameterized batch insert.

The SQL pattern is:

```sql
INSERT INTO public.index_metadata (key, value)
VALUES (%s, %s);
```

On subsequent startup, the adapter validates the expected metadata and
the existing passages table/vector column rather than overwriting metadata.

### 7.4 Insert or update passages atomically

The adapter validates the full batch before opening the write transaction,
then runs this upsert for each record using Psycopg `executemany`:

```sql
INSERT INTO public.passages (
    passage_id, document_id, source_name, page_number, text, embedding
)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (passage_id) DO UPDATE SET
    document_id = EXCLUDED.document_id,
    source_name = EXCLUDED.source_name,
    page_number = EXCLUDED.page_number,
    text = EXCLUDED.text,
    embedding = EXCLUDED.embedding;
```

The batch runs in one transaction: if a database operation fails, the
transaction is rolled back. Avoid manual inserts that bypass the adapter's
provenance and vector validation.

### 7.5 Exact cosine-similarity search

pgvector's `<=>` operator calculates cosine distance. The adapter computes
the application score as `1 - cosine_distance` and orders nearest results
first. The query vector must have the same configured dimension as stored
vectors.

Across all indexed documents, the SQL shape is:

```sql
SELECT
    passage_id,
    document_id,
    source_name,
    page_number,
    text,
    1 - (embedding <=> %s) AS score
FROM public.passages
ORDER BY embedding <=> %s, passage_id
LIMIT %s;
```

With a document filter, the adapter adds a parameterized predicate before
ranking and limiting:

```sql
WHERE document_id = %s
ORDER BY embedding <=> %s, passage_id
LIMIT %s;
```

These fragments are executed by Psycopg with the query vector and limit
passed separately as parameters. A raw SQL example cannot use an abbreviated
vector: a valid vector literal must contain the configured number of numeric
elements. The default is 384.

### 7.6 Count passages

```sql
SELECT COUNT(*)
FROM public.passages;
```

### 7.7 Delete passages for one document

The adapter uses a bound document ID:

```sql
DELETE FROM public.passages
WHERE document_id = %s;
```

Deletion is destructive. To inspect the impact interactively before committing,
use a transaction and keep the rollback until you have checked the affected
rows. Replace the example ID with an actual value:

```sql
BEGIN;

DELETE FROM public.passages
WHERE document_id = 'replace-with-a-known-document-id'
RETURNING passage_id, document_id, source_name, page_number;

-- Review the returned rows. Use ROLLBACK to discard this test deletion.
ROLLBACK;
```

Only replace `ROLLBACK` with `COMMIT` when you intentionally want to
permanently delete those passages. Deleting passages does not delete the
source PDF or any separate file.

## 8. Test database operations

The integration-test database is configured by `POSTGRES_TEST_DB` and should
normally be `ai_document_intelligence_test`. Confirm the active target
before running test commands:

```sql
SELECT current_database(), current_user;
```

Connect explicitly to the test database from the Compose container:

```bash
docker compose exec db sh -lc \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "ai_document_intelligence_test" -c "SELECT current_database(), current_user;"'
```

Do not run test cleanup queries against the development database. The
integration tests are allowed to clear test passage records and use temporary
trigger objects; they must target the dedicated test database.

## 9. Safe operational notes

- The Compose initialization SQL at `docker/postgres/init/01-init.sql`
  enables pgvector and creates/grants the application role on first database
  initialization. Initialization scripts do not automatically re-run against
  an already-initialized named volume.
- The Python adapter creates and validates `public.index_metadata`,
  `public.passages`, and `idx_passages_document_id` when needed.
- Do not change `vector(n)`, the model name, or embedding settings without
  a planned compatibility/re-indexing decision.
- Do not manually update index metadata just to make a configuration check
  pass; metadata is a compatibility guard, not a migration tool.
- Use parameterized SQL in Python, avoid embedding untrusted values into
  SQL strings, and keep passwords out of source code and logs.
- Never run `docker compose down -v` unless deleting the PostgreSQL data
  volume is intentional.
- Keep the development and integration-test databases separate.

## 10. Related documentation

- [Local PostgreSQL and pgvector setup](postgresql-setup.md)
- [PostgreSQL vector-index low-level design](../low-level-design/04-local-vector-index.md)
- [V1 retrieval evaluation record](retrieval-evaluation-v1/README.md)
