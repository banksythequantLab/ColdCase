"""Smoke test: list tables, vector indexes, and judge schema isolation."""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.environ["CRDB_ADMIN_URL"]
conn = psycopg.connect(url, autocommit=True)

print(conn.execute("SELECT version()").fetchone()[0][:60])
tables = [r[0] for r in conn.execute(
    "SELECT table_name FROM coldcase.information_schema.tables"
    " WHERE table_schema='public' ORDER BY 1").fetchall()]
print("public tables:", tables)
judge = [r[0] for r in conn.execute(
    "SELECT table_name FROM coldcase.information_schema.tables"
    " WHERE table_schema='judge'").fetchall()]
print("judge tables:", judge)
vec = conn.execute(
    "SELECT index_name FROM [SHOW INDEXES FROM coldcase.public.email_chunks]"
    " WHERE index_name LIKE '%embedding%' LIMIT 1").fetchall()
print("vector index on email_chunks:", vec)
