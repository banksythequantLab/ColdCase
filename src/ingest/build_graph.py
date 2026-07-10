"""Build comm_edges + person_profiles (graph stats) after ingestion.

Usage: python src/ingest/build_graph.py
Centroid embeddings stay NULL until the embedding phase.
"""
import os
import time

import networkx as nx
import psycopg
from dotenv import load_dotenv

load_dotenv()
conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
t0 = time.time()

print("aggregating comm_edges (server-side)...", flush=True)
conn.execute("DELETE FROM comm_edges WHERE true")
conn.execute("""
  INSERT INTO comm_edges (src, dst, msg_count, first_at, last_at)
  SELECT e.sender_id, r.person_id, count(*), min(e.sent_at), max(e.sent_at)
  FROM emails e JOIN email_recipients r USING (email_id)
  WHERE e.sender_id IS NOT NULL
  GROUP BY 1, 2""")
n_edges = conn.execute("SELECT count(*) FROM comm_edges").fetchone()[0]
print(f"comm_edges: {n_edges} ({time.time()-t0:.0f}s)", flush=True)

print("loading graph for centrality...", flush=True)
G = nx.DiGraph()
for s, d, w in conn.execute("SELECT src, dst, msg_count FROM comm_edges"):
    G.add_edge(str(s), str(d), weight=w)
print(f"graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges",
      flush=True)

pagerank = nx.pagerank(G, weight="weight")
print(f"pagerank done ({time.time()-t0:.0f}s)", flush=True)
btw = nx.betweenness_centrality(G, k=min(150, G.number_of_nodes()),
                                seed=42)
print(f"betweenness (approx, k=150) done ({time.time()-t0:.0f}s)", flush=True)

print("computing sent/recv/after-hours stats (server-side)...", flush=True)
stats = {}
for pid, sent, ah in conn.execute("""
    SELECT sender_id, count(*),
           avg(CASE WHEN EXTRACT(hour FROM sent_at) NOT BETWEEN 8 AND 18
               THEN 1.0 ELSE 0.0 END)
    FROM emails WHERE sender_id IS NOT NULL GROUP BY 1"""):
    stats[str(pid)] = {"sent": sent, "ah": float(ah or 0)}
recv = dict(conn.execute(
    "SELECT person_id::STRING, count(*) FROM email_recipients GROUP BY 1"))

print("writing person_profiles...", flush=True)
conn.execute("DELETE FROM person_profiles WHERE true")
all_pids = {r[0] for r in conn.execute("SELECT person_id::STRING FROM persons")}
rows = []
for pid in all_pids:
    s = stats.get(pid, {})
    rows.append((pid, s.get("sent", 0), recv.get(pid, 0),
                 btw.get(pid, 0.0), pagerank.get(pid, 0.0),
                 s.get("ah", 0.0)))
with conn.cursor() as cur:
    with cur.copy("COPY person_profiles (person_id, sent_count, recv_count,"
                  " betweenness, pagerank, after_hours_ratio)"
                  " FROM STDIN") as cp:
        for r in rows:
            cp.write_row(r)
print(f"person_profiles: {len(rows)} rows ({time.time()-t0:.0f}s)")

print("\nTop 5 bridge nodes (betweenness):")
for name, b in conn.execute("""
    SELECT coalesce(p.real_name, p.full_name), pp.betweenness
    FROM person_profiles pp JOIN persons p USING (person_id)
    ORDER BY pp.betweenness DESC LIMIT 5"""):
    print(f"  {name:<40} {b:.5f}")
