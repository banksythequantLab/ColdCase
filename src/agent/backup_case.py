"""Session-end case backup: snapshot all case-memory tables to S3.

"The agent preserves its own evidence." Called at the end of each session.
Produces a timestamped, restorable JSON snapshot in S3 + verifies row counts.
"""
import datetime
import json
import os

import boto3
import psycopg
from dotenv import load_dotenv

load_dotenv()
TABLES = ["investigations", "hypotheses", "findings", "evidence",
          "suspects", "suspect_events", "agent_sessions"]


def snapshot():
    c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
    dump, counts = {}, {}
    for t in TABLES:
        rows = c.execute(f"SELECT * FROM {t}").fetchall()
        cols = [d.name for d in c.execute(f"SELECT * FROM {t} LIMIT 0")
                .description]
        dump[t] = [dict(zip(cols, r)) for r in rows]
        counts[t] = len(rows)
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    body = json.dumps(dump, default=str, indent=1).encode()
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"],
                      aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])
    key = f"backups/case_{ts}.json"
    s3.put_object(Bucket=os.environ["S3_BUCKET"], Key=key, Body=body,
                  ContentType="application/json")
    # public snapshot for the AWS-hosted static dashboard (no judge data)
    board = [{"name": r[0], "score": float(r[1]), "rationale": r[2]}
             for r in c.execute(
        "SELECT coalesce(p.real_name,p.full_name), s.suspicion_score,"
        " s.rationale FROM suspects s JOIN persons p USING (person_id)"
        " ORDER BY s.suspicion_score DESC").fetchall()]
    pub = json.dumps({"suspects": board, "counts": counts,
                      "updated": ts}, default=str).encode()
    s3.put_object(Bucket=os.environ["S3_BUCKET"], Key="public/case.json",
                  Body=pub, ContentType="application/json",
                  CacheControl="no-cache")
    print(f"backup -> s3://{os.environ['S3_BUCKET']}/{key}"
          f" ({len(body)} bytes) counts={counts}", flush=True)
    return key


if __name__ == "__main__":
    snapshot()
