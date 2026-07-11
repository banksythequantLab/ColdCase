"""Create S3 bucket; upload raw corpus + generated case reports.

AWS service for the hackathon requirement (artifact/document storage).
Usage: python src/s3_sync.py
"""
import json
import os

import boto3
import psycopg
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()
REGION = os.environ["AWS_REGION"]
BUCKET = os.environ["S3_BUCKET"]
s3 = boto3.client("s3", region_name=REGION,
                  aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])


def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
        print(f"bucket exists: {BUCKET}")
    except ClientError:
        kw = {} if REGION == "us-east-1" else {
            "CreateBucketConfiguration": {"LocationConstraint": REGION}}
        s3.create_bucket(Bucket=BUCKET, **kw)
        print(f"created bucket: {BUCKET}")


def export_case_report():
    """Pull current case memory into a JSON report and upload."""
    c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
    suspects = [{"name": r[0], "score": float(r[1]), "rationale": r[2]}
                for r in c.execute(
        "SELECT coalesce(p.real_name,p.full_name), s.suspicion_score,"
        " s.rationale FROM suspects s JOIN persons p USING (person_id)"
        " ORDER BY s.suspicion_score DESC").fetchall()]
    findings = [{"summary": r[0], "method": r[1]} for r in c.execute(
        "SELECT summary, method FROM findings ORDER BY created_at").fetchall()]
    report = {"case": "Enron", "suspects": suspects, "findings": findings,
              "sessions": c.execute(
                  "SELECT count(*) FROM agent_sessions").fetchone()[0]}
    body = json.dumps(report, indent=2).encode()
    s3.put_object(Bucket=BUCKET, Key="reports/enron_case.json", Body=body,
                  ContentType="application/json")
    print(f"uploaded reports/enron_case.json ({len(body)} bytes,"
          f" {len(suspects)} suspects)")


def upload_corpus():
    key = "corpus/enron_mail_20150507.tar.gz"
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        print(f"corpus already uploaded: {key}")
    except ClientError:
        path = "data/enron_mail_20150507.tar.gz"
        print(f"uploading {path} (423MB)...", flush=True)
        s3.upload_file(path, BUCKET, key)
        print(f"uploaded {key}")


if __name__ == "__main__":
    ensure_bucket()
    export_case_report()
    upload_corpus()
    print("\nS3 contents:")
    for o in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []):
        print(f"  {o['Key']:<45} {o['Size']:>12,} bytes")
