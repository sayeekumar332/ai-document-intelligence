\getenv app_user APP_DB_USER
\getenv app_password APP_DB_PASSWORD
\getenv db_name POSTGRES_DB

CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password';

GRANT CONNECT ON DATABASE :"db_name" TO :"app_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"app_user";
GRANT USAGE ON TYPE public.vector TO :"app_user";
