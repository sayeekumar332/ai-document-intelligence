# Local PostgreSQL and pgvector Setup

This guide documents the PostgreSQL environment used by the AI Document
Intelligence project on macOS with Apple Silicon.

## 1. Prerequisites

The verified environment uses:
- Python 3.12 and the project virtual environment.
- Docker Desktop and Docker Compose.
- PostgreSQL 17.11.
- pgvector 0.8.7.
- Psycopg 3.3.6.
- Python pgvector package 0.5.1.

Start Docker Desktop and verify the engine:

```bash
open -a Docker
docker info --format 'Docker Engine server version: {{.ServerVersion}}'
```

## 2. Environment configuration and credentials

Copy `.env.example` to `.env` and configure the required settings:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST_PORT`
- `APP_DB_USER`
- `APP_DB_PASSWORD`
- `POSTGRES_TEST_DB`

The development database is `ai_document_intelligence`. The separate
integration-test database is `ai_document_intelligence_test`.

Use strong passwords. Never overwrite an existing `.env` without
reviewing it locally. Never commit or share its contents.

Verify that `.env` is ignored:

```bash
git check-ignore -v .env
```

Load the environment for Python commands:

```bash
set -a
source .env
set +a
```

Docker Compose reads `.env` for substitution; host Python requires the
variables to be exported into its process environment separately.

## 3. Start PostgreSQL

The project uses the versioned image
`pgvector/pgvector:0.8.7-pg17-bookworm`.

Validate and start the database:

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

Wait for the `db` service to report healthy. The host port is bound to
`127.0.0.1:54329`.

If startup fails, inspect the logs:

```bash
docker compose logs --tail=100 db
```

PostgreSQL data is persisted in the named Docker volume `pgvector_data`.

## 4. Verify PostgreSQL and pgvector

Check the PostgreSQL version:

```bash
docker compose exec db sh -lc \
  'psql -X -A -t -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW server_version;"'
```

Verify the extension:

```bash
docker compose exec db sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dx vector"'
```

The verified versions are PostgreSQL 17.11 and pgvector 0.8.7.

## 5. Application account

The Python adapter should connect as `ai_document_app`, not as the
administrator account.

Test application connectivity without printing the password:

```bash
docker compose exec db sh -lc \
  'PGPASSWORD="$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB" -c "SELECT current_database(), current_user;"'
```

The initialization scripts under `docker/postgres/init/` run only when
the data volume is initialized for the first time. Changes to `.env` or
the scripts do not automatically update existing roles or passwords.

## 6. Create the integration-test database

This is a one-time setup operation:

```bash
docker compose exec db sh -lc \
  'createdb -U "$POSTGRES_USER" ai_document_intelligence_test'
```

Enable pgvector and grant the application account access:

```bash
docker compose exec db sh -lc \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d ai_document_intelligence_test -c "CREATE EXTENSION IF NOT EXISTS vector; GRANT CONNECT ON DATABASE ai_document_intelligence_test TO ai_document_app; GRANT USAGE, CREATE ON SCHEMA public TO ai_document_app; GRANT USAGE ON TYPE public.vector TO ai_document_app;"'
```

Verify the test database:

```bash
docker compose exec db sh -lc \
  'psql -X -A -t -U "$POSTGRES_USER" -d ai_document_intelligence_test -c "SELECT current_database(), extversion FROM pg_extension WHERE extname = '\''vector'\'';"'
```

The integration tests must target `POSTGRES_TEST_DB`, set to
`ai_document_intelligence_test`, not the development database. The
tests clear passage records and use temporary trigger objects.

Do not rerun `createdb` if the database already exists.

## 7. Install Python dependencies

Activate the virtual environment and install the project:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pip check
```

The project declares Psycopg 3 and the Python pgvector package in
`pyproject.toml`.

Load `.env` into the current shell when needed:

```bash
set -a
source .env
set +a
```

## 8. Run tests

Run the PostgreSQL integration tests:

```bash
python -m pytest tests/integration/test_postgres_vector_index.py -v
```

Run the complete verification suite:

```bash
python -m ruff check .
python -m pytest
python -m pip check
git diff --check
```

The recorded result after adding PostgreSQL integration tests was
51 passed, with five non-fatal SWIG-related deprecation warnings.

## 9. Stop and restart safely

Stop the database without deleting its data:

```bash
docker compose stop
```

Restart it:

```bash
docker compose start
docker compose ps
```

To remove the container and network while preserving the named volume:

```bash
docker compose down
```

**Data safety:** do not use `docker compose down -v` unless you
intentionally want to delete the named volume and its persisted data.

Never commit `.env`, passwords, private PDFs, database files, or generated
embedding data.
