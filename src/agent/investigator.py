"""Cold Case investigator agent — session loop.

Usage:
  python src/agent/investigator.py --new-case "Enron"
  python src/agent/investigator.py --resume  (uses CASE_ID from .env)

Status: SKELETON — untested. Week 2-3 deliverable.
Loop: resume memory -> pick open hypothesis -> investigate (Bedrock Claude
tool-use loop, max MAX_TOOL_CALLS_PER_SESSION) -> write findings/suspects ->
session summary -> exit. Persistence lives entirely in CockroachDB, so
killing this process mid-session loses nothing.
"""
import os

import boto3
import psycopg
from dotenv import load_dotenv

load_dotenv()


def resume_memory(conn, case_id):
    """Read open hypotheses, last session summaries, top suspects."""
    hyps = conn.execute(
        "SELECT hypothesis_id, statement, confidence FROM hypotheses"
        " WHERE case_id=%s AND status='open'", (case_id,)).fetchall()
    sessions = conn.execute(
        "SELECT summary FROM agent_sessions WHERE case_id=%s"
        " ORDER BY started_at DESC LIMIT 3", (case_id,)).fetchall()
    suspects = conn.execute(
        "SELECT person_id, suspicion_score, rationale FROM suspects"
        " WHERE case_id=%s ORDER BY suspicion_score DESC LIMIT 10",
        (case_id,)).fetchall()
    return hyps, sessions, suspects


def run_session(case_id):
    bedrock = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
    conn = psycopg.connect(os.environ["CRDB_URL"])
    # TODO Week 2-3: Bedrock converse() tool-use loop wiring tools.py
    raise NotImplementedError


if __name__ == "__main__":
    run_session(os.environ.get("CASE_ID"))
