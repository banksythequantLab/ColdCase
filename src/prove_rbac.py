"""Prove the agent's DB role cannot read the sealed ground truth.

Connects as the least-privilege agent role (CRDB_URL) and attempts to read
judge.poi_labels. The denial is the proof that the investigation was blind.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
print("Connecting as the agent role (coldcase_agent)...")
c = psycopg.connect(os.environ["CRDB_URL"], autocommit=True)

print("\n[1] Agent CAN read its own case memory:")
n = c.execute("SELECT count(*) FROM suspects").fetchone()[0]
print(f"    SELECT count(*) FROM suspects  ->  {n} rows  (allowed)")

print("\n[2] Agent CAN read the evidence corpus:")
n = c.execute("SELECT count(*) FROM financial_profiles").fetchone()[0]
print(f"    SELECT count(*) FROM financial_profiles  ->  {n} rows  (allowed)")

print("\n[3] Agent attempts to read the SEALED ground truth:")
try:
    c.execute("SELECT * FROM judge.poi_labels LIMIT 1").fetchone()
    print("    !!! FAILURE: agent read the answer key - blindness broken")
except psycopg.errors.InsufficientPrivilege as e:
    print("    SELECT * FROM judge.poi_labels")
    print(f"    ->  DENIED: {str(e).splitlines()[0]}")
    print("\n    The 18 POI labels are unreadable by the agent. The")
    print("    investigation is provably blind - enforced by RBAC, not trust.")
