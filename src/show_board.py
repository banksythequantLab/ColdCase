import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
mc = c.execute("SELECT case_id FROM investigations WHERE title NOT LIKE"
               " 'ablation%' ORDER BY created_at LIMIT 1").fetchone()[0]
for r in c.execute(
        "SELECT coalesce(p.real_name,p.full_name), s.suspicion_score,"
        " coalesce(j.is_poi,false) FROM suspects s JOIN persons p"
        " USING(person_id) LEFT JOIN judge.poi_labels j USING(person_id)"
        " WHERE s.case_id=%s ORDER BY s.suspicion_score DESC", (mc,)).fetchall():
    print(f"{r[0]:<24} {float(r[1]):.2f}  {'[POI]' if r[2] else '-'}")
