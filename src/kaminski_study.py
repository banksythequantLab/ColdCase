"""Pull the REAL Kaminski case data for the whistleblower case study.

No fabricated timelines - just what's actually in CockroachDB + the experiment
verdicts. Kaminski is Enron's head of risk who WARNED against the deals; the
agent flagged him (a false positive). This shows the evidence store preserving
the nuance.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
pid = c.execute("SELECT person_id FROM persons WHERE real_name="
                "'KAMINSKI WINCENTY J'").fetchone()[0]

print("=== SUSPECT ROW ===")
for r in c.execute("SELECT suspicion_score, rationale FROM suspects"
                   " WHERE person_id=%s", (pid,)).fetchall():
    print(f"score={r[0]}  rationale={r[1][:200]}")

print("\n=== HYPOTHESES ABOUT KAMINSKI ===")
for r in c.execute(
    "SELECT h.status, h.confidence, h.statement FROM hypotheses h"
    " WHERE h.statement ILIKE '%kaminski%' ORDER BY h.updated_at").fetchall():
    print(f"[{r[0]} {r[1]}] {r[2][:220]}")

print("\n=== SCORE HISTORY (suspect_events) ===")
for r in c.execute("SELECT ts, suspicion_score, rationale FROM suspect_events"
                   " WHERE person_id=%s ORDER BY ts", (pid,)).fetchall():
    print(f"{str(r[0])[:19]}  score={r[1]}  {r[2][:110]}")

print("\n=== SAMPLE OF HIS OWN EMAILS ON RISK/SPV (stance evidence) ===")
for r in c.execute(
    "SELECT left(e.body,180) FROM emails e WHERE e.sender_id=%s"
    " AND (e.body ILIKE '%risk%' OR e.body ILIKE '%raptor%'"
    " OR e.body ILIKE '%LJM%') ORDER BY e.sent_at DESC LIMIT 3",
    (pid,)).fetchall():
    print("-", r[0].replace(chr(10), " ").strip()[:150])
