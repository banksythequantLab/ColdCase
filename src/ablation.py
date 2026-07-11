"""Ablation: does persistent CockroachDB memory actually help?

NO-MEMORY arm: each session starts a FRESH case with no resume context — the
agent cannot build on prior sessions. We run several and report the best/avg.
MEMORY arm: the accumulated case that resumed across sessions (already run).

Scores each arm blind against the sealed POI labels.
Usage: python src/ablation.py <n_no_memory_sessions>
"""
import json
import os
import sys

import psycopg
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
import investigator as INV

load_dotenv()
admin = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)


def score(case_id):
    rows = admin.execute("""
      SELECT coalesce(j.is_poi,false), s.suspicion_score
      FROM suspects s LEFT JOIN judge.poi_labels j USING (person_id)
      WHERE s.case_id=%s ORDER BY s.suspicion_score DESC""",
      (case_id,)).fetchall()
    flagged = [r for r in rows if r[1] >= 0.5]
    top3 = rows[:3]
    p3 = sum(1 for r in top3 if r[0]) / len(top3) if top3 else 0
    pois = sum(1 for r in flagged if r[0])
    return {"precision@3": round(p3, 2), "flagged": len(flagged),
            "pois_found": pois, "recall": round(pois / 18, 3)}


def run_no_memory(n):
    results = []
    for i in range(n):
        cid = admin.execute(
            "INSERT INTO investigations (title) VALUES (%s)"
            " RETURNING case_id", (f"ablation-nomem-{i}",)).fetchone()[0]
        conn = psycopg.connect(os.environ["CRDB_URL"], autocommit=True)
        print(f"[no-memory session {i+1}/{n}] case {cid}", flush=True)
        INV.run_session(cid, conn, resume=False)
        results.append(score(cid))
        print("  ->", results[-1], flush=True)
    return results


def main(n):
    # MEMORY arm = the accumulated open case (resumed across many sessions)
    mem_case = admin.execute(
        "SELECT case_id FROM investigations WHERE status='open'"
        " ORDER BY created_at DESC LIMIT 1").fetchone()[0]
    n_sessions = admin.execute(
        "SELECT count(*) FROM agent_sessions WHERE case_id=%s",
        (mem_case,)).fetchone()[0]
    mem = score(mem_case)
    mem["sessions"] = n_sessions

    nomem = run_no_memory(n)
    # aggregate no-memory: best single session (fair — 1 session, no recall)
    best = max(nomem, key=lambda r: (r["pois_found"], r["precision@3"]))
    avg_p3 = round(sum(r["precision@3"] for r in nomem) / len(nomem), 2)
    avg_pois = round(sum(r["pois_found"] for r in nomem) / len(nomem), 1)

    out = {"memory": mem,
           "no_memory_runs": nomem,
           "no_memory_best": best,
           "no_memory_avg": {"precision@3": avg_p3, "avg_pois": avg_pois}}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..",
              "docs", "ablation.json"), "w"), indent=2)
    print("\n=== ABLATION ===")
    print(f"MEMORY   ({mem['sessions']} sessions): P@3={mem['precision@3']}"
          f" recall={mem['recall']} pois={mem['pois_found']}")
    print(f"NO-MEMORY (best of {n}):     P@3={best['precision@3']}"
          f" recall={best['recall']} pois={best['pois_found']}")
    print(f"NO-MEMORY (avg):            P@3={avg_p3} pois={avg_pois}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
