"""Compute person centroids = mean of their sent-email chunk embeddings.

Run AFTER embed_chunks.py completes.
"""
import os
import time

import numpy as np
import psycopg
from dotenv import load_dotenv

load_dotenv()
conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
t0 = time.time()

sums, counts = {}, {}
with conn.cursor(name="stream") as cur:
    cur.itersize = 5000
    cur.execute("""
      SELECT e.sender_id::STRING, c.embedding::STRING
      FROM email_chunks c JOIN emails e USING (email_id)
      WHERE e.sender_id IS NOT NULL""")
    n = 0
    for pid, emb in cur:
        v = np.fromstring(emb[1:-1], sep=",")
        if pid in sums:
            sums[pid] += v
            counts[pid] += 1
        else:
            sums[pid] = v.copy()
            counts[pid] = 1
        n += 1
        if n % 200000 == 0:
            print(f"{n} chunks streamed ({time.time()-t0:.0f}s)", flush=True)

print(f"{n} chunks -> {len(sums)} people; writing centroids...", flush=True)
rows = []
for pid, s in sums.items():
    c = s / counts[pid]
    rows.append(("[" + ",".join(f"{x:.6f}" for x in c) + "]", pid))
with conn.cursor() as cur:
    cur.executemany(
        "UPDATE person_profiles SET centroid = %s::VECTOR"
        " WHERE person_id = %s", rows)
print(f"DONE: {len(rows)} centroids ({time.time()-t0:.0f}s)")
