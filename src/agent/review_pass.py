"""Self-critique pass — EXPERIMENTAL, NOT in the production scoring path.

Negative result: see docs/EXPERIMENTS.md (E3). Stance-from-self-authored-email
demotes real perpetrators too (they don't incriminate themselves in their own
mail), so this must NOT be run against the live board. Retained for the record.

Re-examine every flagged suspect with stance detection and the concealment
gate; demote anyone whose own words don't show they PERPETRATED a scheme.

Usage: python src/agent/review_pass.py
Writes updated scores + an audit trail to suspect_events with method='review'.
"""
import os
import sys

import psycopg
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import stance

load_dotenv()
CAP_NON_PERP = 0.35  # max score if not a perpetrator


def main():
    conn = psycopg.connect(os.environ["CRDB_URL"], autocommit=True)
    case_id = conn.execute(
        "SELECT case_id FROM investigations WHERE status='open'"
        " ORDER BY created_at DESC LIMIT 1").fetchone()[0]
    flagged = conn.execute(
        "SELECT s.person_id::STRING, coalesce(p.real_name, p.full_name),"
        " s.suspicion_score FROM suspects s JOIN persons p USING (person_id)"
        " WHERE s.case_id=%s AND s.suspicion_score >= 0.5"
        " ORDER BY s.suspicion_score DESC", (case_id,)).fetchall()
    print(f"reviewing {len(flagged)} flagged suspects\n", flush=True)
    for pid, name, score in flagged:
        st = stance.classify_stance(pid)
        stc = st.get("stance", "unknown")
        if stc == "perpetrator":
            print(f"KEEP  {name:<22} {score:.2f}  (perpetrator: "
                  f"{st['why'][:60]})", flush=True)
            continue
        new = min(score, CAP_NON_PERP)
        rationale = (f"Review/stance: authored evidence reads as '{stc}', "
                     f"not perpetrator ({st.get('why','')[:90]}). "
                     f"Score capped {score:.2f}->{new:.2f}.")
        conn.execute(
            "UPDATE suspects SET suspicion_score=%s, rationale=%s,"
            " updated_at=now() WHERE case_id=%s AND person_id=%s",
            (new, rationale, case_id, pid))
        conn.execute(
            "INSERT INTO suspect_events (case_id, person_id, suspicion_score,"
            " rationale) VALUES (%s,%s,%s,%s)",
            (case_id, pid, new, rationale))
        print(f"DEMOTE {name:<22} {score:.2f} -> {new:.2f}  ({stc}: "
              f"{st.get('why','')[:55]})", flush=True)
    print("\nreview complete", flush=True)


if __name__ == "__main__":
    main()
