"""Score the agent's suspect board against sealed POI labels (ADMIN ONLY).

The agent role cannot run this — judge schema is unreadable to it.
Usage: python src/score_case.py
"""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])

rows = c.execute("""
  SELECT coalesce(p.real_name, p.full_name), s.suspicion_score,
         coalesce(j.is_poi, false)
  FROM suspects s
  JOIN persons p USING (person_id)
  LEFT JOIN judge.poi_labels j ON j.person_id = s.person_id
  WHERE s.case_id = (SELECT case_id FROM investigations
                     WHERE title NOT LIKE 'ablation%' ORDER BY created_at LIMIT 1)
  ORDER BY s.suspicion_score DESC""").fetchall()
total_pois = c.execute(
    "SELECT count(*) FROM judge.poi_labels WHERE is_poi").fetchone()[0]

print(f"{'SUSPECT':<26} {'SCORE':>5}  POI?")
for name, score, poi in rows:
    print(f"{name:<26} {score:>5.2f}  {'[POI]' if poi else '-'}")

flagged = [(n, s, p) for n, s, p in rows if s >= 0.5]
hits = sum(1 for _, _, p in flagged if p)
for k in (3, 5, 10):
    top = rows[:k]
    tp = sum(1 for _, _, p in top if p)
    if top:
        print(f"precision@{k}: {tp}/{len(top)} = {tp/len(top):.0%}")
print(f"flagged (score>=0.5): {len(flagged)}, of which real POIs: {hits}"
      f" -> precision {hits/len(flagged):.0%}" if flagged else "none flagged")
print(f"recall vs {total_pois} labeled POIs: {hits}/{total_pois}"
      f" = {hits/total_pois:.0%}")
