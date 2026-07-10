import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
print("financial_profiles:",
      c.execute("SELECT count(*) FROM financial_profiles").fetchone()[0])
print("poi_labels:", c.execute(
    "SELECT count(*), count(*) FILTER (WHERE is_poi)"
    " FROM judge.poi_labels").fetchone())
print("\nTop 5 by exercised stock options (with mailbox stats):")
rows = c.execute("""
  SELECT p.real_name, f.exercised_stock_options, f.salary,
         (SELECT count(*) FROM emails e WHERE e.sender_id = p.person_id)
  FROM financial_profiles f JOIN persons p USING (person_id)
  ORDER BY f.exercised_stock_options DESC NULLS LAST LIMIT 5""").fetchall()
for r in rows:
    print(f"  {r[0]:<22} stock=${r[1]:>11,} salary=${r[2] or 0:>9,}"
          f" sent_emails={r[3]}")
