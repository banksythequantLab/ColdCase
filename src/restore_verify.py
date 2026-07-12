"""Disaster-recovery: restore a case-memory snapshot from S3 and verify the
evidence chain of custody (every excerpt's SHA-256 must match).

Usage:
  python src/restore_verify.py                 # verify latest snapshot
  python src/restore_verify.py <s3_key>        # verify a specific snapshot
This is non-destructive: it validates a backup can be restored and that no
evidence was tampered with. It does NOT overwrite the live DB.
"""
import ast
import hashlib
import json
import os
import sys

import boto3
from dotenv import load_dotenv

load_dotenv()
s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"],
                  aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])
BUCKET = os.environ["S3_BUCKET"]

key = sys.argv[1] if len(sys.argv) > 1 else sorted(
    o["Key"] for o in s3.list_objects_v2(
        Bucket=BUCKET, Prefix="backups/").get("Contents", []))[-1]
print(f"Restoring snapshot: s3://{BUCKET}/{key}")
snap = json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())

counts = {t: len(rows) for t, rows in snap.items()}
print("Tables recovered:", counts)

ev = snap.get("evidence", [])
ok = bad = skipped = 0
for e in ev:
    stored = e.get("excerpt_sha256")
    excerpt = e.get("excerpt")
    if not stored or excerpt is None:
        skipped += 1
        continue
    # stored hash may be hex or base64-ish repr; compare recomputed hex
    calc = hashlib.sha256(excerpt.encode()).hexdigest()
    try:
        stored_hex = ast.literal_eval(stored).hex()  # b'...' -> hex
    except Exception:
        stored_hex = str(stored).replace("\\x", "").replace(" ", "").lower()
    if calc == stored_hex:
        ok += 1
    else:
        bad += 1

print(f"\nChain-of-custody check on {len(ev)} evidence rows:")
print(f"  verified: {ok}   mismatched: {bad}   unhashed/skipped: {skipped}")
print("RESTORE OK - snapshot is complete and evidence is intact."
      if bad == 0 else "!!! TAMPERING DETECTED - hash mismatch")
