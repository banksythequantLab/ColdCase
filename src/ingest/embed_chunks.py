"""Embed email bodies locally (fastembed / all-MiniLM-L6-v2, 384-dim).

Usage: python src/ingest/embed_chunks.py
Resumable; drops the vector index during bulk load, rebuilds at the end.
"""
import os
import time
import uuid

import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding

load_dotenv()
CHUNK_CHARS = 1100
MAX_CHUNKS = 6
PAGE = 2000


def chunks_of(subject, body):
    text = (subject or "") + "\n" + (body or "")
    text = text.strip()
    if not text:
        return []
    out = [text[i:i + CHUNK_CHARS]
           for i in range(0, min(len(text), CHUNK_CHARS * MAX_CHUNKS),
                          CHUNK_CHARS)]
    return out


def vec_str(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def main():
    conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
    model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    conn.execute("DROP INDEX IF EXISTS email_chunks@email_chunks_embedding_idx")
    print("vector index dropped for bulk load", flush=True)
    done = {r[0] for r in conn.execute(
        "SELECT DISTINCT email_id FROM email_chunks")}
    print(f"resuming: {len(done)} emails already embedded", flush=True)
    t0, total_emails, total_chunks, last = time.time(), 0, 0, None
    while True:
        q = ("SELECT email_id, subject, body FROM emails"
             + (" WHERE email_id > %s" if last else "")
             + " ORDER BY email_id LIMIT %s")
        args = (last, PAGE) if last else (PAGE,)
        rows = conn.execute(q, args).fetchall()
        if not rows:
            break
        last = rows[-1][0]
        batch = [(eid, seq, txt) for eid, subj, body in rows
                 if eid not in done
                 for seq, txt in enumerate(chunks_of(subj, body))]
        if not batch:
            continue
        vecs = list(model.embed([t for _, _, t in batch], batch_size=256))
        with conn.cursor() as cur:
            with cur.copy("COPY email_chunks (chunk_id, email_id, seq, text,"
                          " embedding) FROM STDIN") as cp:
                for (eid, seq, txt), v in zip(batch, vecs):
                    cp.write_row((uuid.uuid4(), eid, seq, txt, vec_str(v)))
        total_emails += len(rows)
        total_chunks += len(batch)
        if total_emails % 20000 < PAGE:
            r = total_chunks / (time.time() - t0)
            print(f"{total_emails} emails scanned, {total_chunks} chunks"
                  f" embedded ({r:.0f} chunks/s)", flush=True)

    print(f"embedding done: {total_chunks} chunks in"
          f" {time.time()-t0:.0f}s — rebuilding vector index...", flush=True)
    conn.execute("SET statement_timeout = 0")
    conn.execute("CREATE VECTOR INDEX IF NOT EXISTS"
                 " email_chunks_embedding_idx ON email_chunks (embedding)")
    print(f"DONE: index rebuilt ({time.time()-t0:.0f}s total)", flush=True)


if __name__ == "__main__":
    main()
