"""Parse the CMU Enron maildir into CockroachDB.

Usage: python src/ingest/parse_maildir.py data/maildir
Status: SKELETON — untested. Week 1 milestone deliverable.
"""
import email.utils
import hashlib
import os
import sys
from email import message_from_file
from email.policy import compat32

import psycopg
from dotenv import load_dotenv

load_dotenv()
BATCH = 500


def parse_message(path):
    """Return (message_id, sender, recipients, sent_at, subject, body, folder)."""
    with open(path, "r", errors="replace") as f:
        msg = message_from_file(f, policy=compat32)
    body = msg.get_payload(decode=False)
    if not isinstance(body, str):
        body = ""
    return {
        "message_id": msg.get("Message-ID"),
        "sender": (msg.get("From") or "").strip().lower(),
        "to": email.utils.getaddresses(msg.get_all("To", [])),
        "cc": email.utils.getaddresses(msg.get_all("Cc", [])),
        "bcc": email.utils.getaddresses(msg.get_all("Bcc", [])),
        "sent_at": email.utils.parsedate_to_datetime(msg.get("Date"))
        if msg.get("Date") else None,
        "subject": msg.get("Subject") or "",
        "body": body,
        "sha256": hashlib.sha256(body.encode("utf-8", "replace")).digest(),
    }


def walk_maildir(root):
    for dirpath, _, files in os.walk(root):
        folder = os.path.relpath(dirpath, root)
        for name in files:
            yield folder, os.path.join(dirpath, name)


def main(root):
    conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
    seen, batch, total = set(), [], 0
    for folder, path in walk_maildir(root):
        try:
            m = parse_message(path)
        except Exception:
            continue  # log in real run
        if not m["message_id"] or m["message_id"] in seen:
            continue
        seen.add(m["message_id"])
        batch.append((m, folder))
        if len(batch) >= BATCH:
            total += flush(conn, batch)
            batch = []
    if batch:
        total += flush(conn, batch)
    print(f"Ingested {total} unique emails")


def flush(conn, batch):
    """TODO Week 1: resolve persons (sender/recipient upsert by address),
    insert emails + email_recipients in one transaction per batch."""
    raise NotImplementedError


if __name__ == "__main__":
    main(sys.argv[1])
