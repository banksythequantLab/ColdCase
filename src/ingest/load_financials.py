"""Load Udacity POI financial dataset into financial_profiles + judge.poi_labels.

Usage: python src/ingest/load_financials.py data/final_project_dataset.pkl
"""
import os
import pickle
import sys
import uuid

import psycopg
from dotenv import load_dotenv

load_dotenv()

EXCLUDE = {"TOTAL", "THE TRAVEL AGENCY IN THE PARK"}
FIN_COLS = ["salary", "bonus", "total_payments", "loan_advances",
            "deferred_income", "exercised_stock_options", "restricted_stock",
            "total_stock_value", "long_term_incentive", "expenses",
            "director_fees", "other", "deferral_payments",
            "restricted_stock_deferred"]

DDL = [
    "ALTER TABLE persons ADD COLUMN IF NOT EXISTS real_name STRING",
    "ALTER TABLE financial_profiles ADD COLUMN IF NOT EXISTS"
    " deferral_payments INT8",
    "ALTER TABLE financial_profiles ADD COLUMN IF NOT EXISTS"
    " restricted_stock_deferred INT8",
]


def val(v):
    return None if v in ("NaN", None) else int(v)


def guess_addr(name):
    """'LAY KENNETH L' -> kenneth.lay@enron.com"""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[1].lower()}.{parts[0].lower()}@enron.com"
    return None


def resolve(conn, name, addr):
    """Return person_id: by dataset address, by guessed address, or new row."""
    for candidate in (addr, guess_addr(name)):
        if not candidate:
            continue
        row = conn.execute(
            "SELECT person_id FROM persons WHERE full_name = %s",
            (candidate,)).fetchone()
        if row:
            conn.execute(
                "UPDATE persons SET real_name = %s WHERE person_id = %s",
                (name, row[0]))
            return row[0], candidate
    pid = uuid.uuid4()
    conn.execute(
        "INSERT INTO persons (person_id, full_name, emails, real_name)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (full_name) DO NOTHING",
        (pid, name, [], name))
    return pid, None


def main(pkl_path):
    with open(pkl_path, "rb") as f:
        data = pickle.load(f, encoding="latin1")
    conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
    for ddl in DDL:
        conn.execute(ddl)
    matched, guessed, created, pois = 0, 0, 0, 0
    for name, feats in sorted(data.items()):
        if name in EXCLUDE:
            continue
        pid, addr = resolve(conn, name, feats.get("email_address")
                            if feats.get("email_address") != "NaN" else None)
        if addr == feats.get("email_address"):
            matched += 1
        elif addr:
            guessed += 1
        else:
            created += 1
        cols = ", ".join(FIN_COLS)
        ph = ", ".join(["%s"] * len(FIN_COLS))
        upd = ", ".join(f"{c} = excluded.{c}" for c in FIN_COLS)
        conn.execute(
            f"INSERT INTO financial_profiles (person_id, {cols})"
            f" VALUES (%s, {ph}) ON CONFLICT (person_id) DO UPDATE SET {upd}",
            (pid, *[val(feats.get(c)) for c in FIN_COLS]))
        conn.execute(
            "UPSERT INTO judge.poi_labels (person_id, is_poi) VALUES (%s, %s)",
            (pid, bool(feats.get("poi"))))
        pois += bool(feats.get("poi"))
    print(f"DONE: {matched} matched by dataset email, {guessed} by guessed"
          f" address, {created} created without mailbox; {pois} POIs labeled")


if __name__ == "__main__":
    main(sys.argv[1])
