"""Ingest + embed the SEC filings into CockroachDB as a source-tagged
documents corpus, indexed with C-SPANN alongside the emails.
"""
import glob
import os
import uuid

import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding

load_dotenv()
SEC = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sec")
CHUNK = 1100

DDL = """
DROP TABLE IF EXISTS doc_chunks;
DROP TABLE IF EXISTS documents;
CREATE TABLE documents (
  doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source STRING, form STRING, filed DATE, title STRING
);
CREATE TABLE doc_chunks (
  chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_id UUID REFERENCES documents,
  seq INT2, text STRING, embedding VECTOR(384)
);
"""


def gpu_model():
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        import src.gpu_setup as g  # noqa
    except Exception:
        pass
    try:
        from gpu_setup import enable_cuda_dlls
        enable_cuda_dlls()
        return TextEmbedding("sentence-transformers/all-MiniLM-L6-v2",
                             providers=["CUDAExecutionProvider",
                                        "CPUExecutionProvider"])
    except Exception:
        return TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")


def chunks(text):
    return [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]


def main():
    c = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
    for stmt in DDL.strip().split(";"):
        if stmt.strip():
            c.execute(stmt)
    c.execute("GRANT SELECT ON TABLE coldcase.public.documents,"
              " coldcase.public.doc_chunks TO coldcase_agent")
    model = gpu_model()
    files = sorted(glob.glob(os.path.join(SEC, "*.txt")))
    total = 0
    for path in files:
        txt = open(path, encoding="utf-8").read()
        head = txt.split("\n", 1)[0]
        parts = [p.strip() for p in head.split("|")]
        form = parts[1] if len(parts) > 1 else "?"
        filed = parts[2].replace("filed ", "") if len(parts) > 2 else None
        did = uuid.uuid4()
        c.execute("INSERT INTO documents (doc_id, source, form, filed, title)"
                  " VALUES (%s,'SEC EDGAR',%s,%s,%s)",
                  (did, form, filed, os.path.basename(path)))
        cks = chunks(txt)
        vecs = list(model.embed(cks, batch_size=128))
        with c.cursor() as cur:
            with cur.copy("COPY doc_chunks (chunk_id, doc_id, seq, text,"
                          " embedding) FROM STDIN") as cp:
                for i, (t, v) in enumerate(zip(cks, vecs)):
                    cp.write_row((uuid.uuid4(), did, i, t,
                                  "[" + ",".join(f"{x:.6f}" for x in v) + "]"))
        total += len(cks)
        print(f"  {os.path.basename(path)}: {len(cks)} chunks", flush=True)
    print("building C-SPANN vector index...", flush=True)
    c.execute("SET statement_timeout = 0")
    c.execute("CREATE VECTOR INDEX IF NOT EXISTS doc_chunks_embedding_idx"
              " ON doc_chunks (embedding)")
    print(f"DONE: {len(files)} filings, {total} chunks embedded + indexed")


if __name__ == "__main__":
    main()
