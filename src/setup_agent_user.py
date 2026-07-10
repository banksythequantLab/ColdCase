"""Create coldcase_agent SQL user, apply least-privilege grants, prove RBAC.

Password is generated locally and written to .env only.
"""
import os
import re
import secrets

import psycopg
from dotenv import load_dotenv

ROOT = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(ROOT, ".env"))

admin = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
pw = secrets.token_urlsafe(24)
admin.execute("REVOKE ALL ON coldcase.public.* FROM coldcase_agent")
admin.execute("DROP USER IF EXISTS coldcase_agent")
admin.execute(f"CREATE USER coldcase_agent WITH PASSWORD '{pw}'")
with open(os.path.join(ROOT, "sql", "grants.sql")) as f:
    sql = "\n".join(ln for ln in f.read().splitlines()
                    if not ln.strip().startswith("--"))
grants = [s.strip() for s in sql.split(";") if s.strip()]
for g in grants:
    admin.execute(g)
print("user created; grants applied:", len(grants))

agent_url = re.sub(r"//[^@]+@", f"//coldcase_agent:{pw}@",
                   os.environ["CRDB_ADMIN_URL"])
env_path = os.path.join(ROOT, ".env")
with open(env_path) as f:
    env = f.read()
env = re.sub(r"CRDB_URL=.*", f"CRDB_URL={agent_url}", env, count=1)
with open(env_path, "w") as f:
    f.write(env)
print(".env updated with CRDB_URL (agent)")

# RBAC proof
agent = psycopg.connect(agent_url, autocommit=True)
n = agent.execute("SELECT count(*) FROM financial_profiles").fetchone()[0]
print(f"agent CAN read financial_profiles: {n} rows")
agent.execute("INSERT INTO investigations (title) VALUES ('rbac smoke test')")
print("agent CAN write case memory (investigations)")
try:
    agent.execute("SELECT count(*) FROM judge.poi_labels")
    print("!!! FAIL: agent read the ground truth — fix grants")
except psycopg.errors.InsufficientPrivilege as e:
    print("agent CANNOT read judge.poi_labels ->",
          str(e).splitlines()[0])
admin.execute("DELETE FROM investigations WHERE title = 'rbac smoke test'")
print("smoke-test row cleaned up")
