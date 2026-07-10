"""Parse the CMU Enron maildir into CockroachDB.

Usage: python src/ingest/parse_maildir.py D:\\ColdCase_data\\maildir
Resumable: preloads existing message_ids and skips them.
"""
import email.utils
import hashlib
import os
import sys
import time
import uuid
from email import message_from_file
from email.policy import compat32

import psycopg
from dotenv import load_dotenv

load_dotenv()
BATCH = 1000


def get_body(msg):
    if msg.is_multipart():
        parts = [p.get_payload(decode=False) for p in msg.walk()]
        return "\n".join(p for p in parts if isinstance(p, str))
    pl = msg.get_payload(decode=False)
    return pl if isinstance(pl, str) else ""


def winpath(path):
    """Enron filenames end with '.', which Win32 strips; \\\\?\\ disables that."""
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + path  # no abspath: it strips trailing dots too
    return path


def parse_message(path):
    with open(winpath(path), "r", errors="replace") as f:
        msg = message_from_file(f, policy=compat32)
    body = get_body(msg)
    try:
        sent_at = email.utils.parsedate_to_datetime(msg.get("Date"))
    except Exception:
        sent_at = None
    def addrs(header):
        return sorted({a[1].lower() for a in
                       email.utils.getaddresses(msg.get_all(header, []))
                       if a[1] and "@" in a[1]})
    return {
        "message_id": (msg.get("Message-ID") or "").strip(),
        "sender": email.utils.parseaddr(msg.get("From") or "")[1].lower(),
        "to": addrs("To"), "cc": addrs("Cc"), "bcc": addrs("Bcc"),
        "sent_at": sent_at,
        "subject": msg.get("Subject") or "",
        "body": body,
        "sha256": hashlib.sha256(body.encode("utf-8", "replace")).digest(),
    }


def walk_maildir(root):
    for dirpath, _, files in os.walk(root):
        folder = os.path.relpath(dirpath, root).replace("\\", "/")
        for name in files:
            yield folder, os.path.join(dirpath, name)


class PersonCache:
    """address -> person_id, in memory; new persons batched per flush."""
    def __init__(self, conn):
        self.map = {}
        for pid, addr_list in conn.execute(
                "SELECT person_id, emails FROM persons"):
            for a in addr_list:
                self.map[a] = pid
        self.pending = []  # (person_id, full_name, [addr])

    def get(self, addr):
        if addr not in self.map:
            pid = uuid.uuid4()
            self.map[addr] = pid
            self.pending.append((pid, addr, [addr]))
        return self.map[addr]

    def take_pending(self):
        p, self.pending = self.pending, []
        return p


def flush(conn, people, batch):
    """Phase A: resolve persons (self-healing upsert). Phase B: COPY emails."""
    addrs = {m["sender"] for m, _ in batch}
    for m, _ in batch:
        for kind in ("to", "cc", "bcc"):
            addrs.update(m[kind])
    for a in addrs:
        people.get(a)
    persons_rows = people.take_pending()
    if persons_rows:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO persons (person_id, full_name, emails)"
                " VALUES (%s,%s,%s) ON CONFLICT (full_name) DO NOTHING",
                persons_rows)
        names = [r[1] for r in persons_rows]
        for pid, name in conn.execute(
                "SELECT person_id, full_name FROM persons"
                " WHERE full_name = ANY(%s)", (names,)):
            people.map[name] = pid  # canonical DB ids win
    email_rows, rcpt_rows = [], []
    for m, folder in batch:
        eid = uuid.uuid4()
        email_rows.append((eid, m["message_id"], people.get(m["sender"]),
                           m["sent_at"], m["subject"], m["body"], folder,
                           m["sha256"]))
        seen = set()
        for kind in ("to", "cc", "bcc"):
            for a in m[kind]:
                pid = people.get(a)
                if (pid, kind) not in seen:
                    seen.add((pid, kind))
                    rcpt_rows.append((eid, pid, kind))
    with conn.transaction():
        with conn.cursor() as cur:
            with cur.copy("COPY emails (email_id, message_id, sender_id,"
                          " sent_at, subject, body, folder, body_sha256)"
                          " FROM STDIN") as cp:
                for r in email_rows:
                    cp.write_row(r)
            if rcpt_rows:
                with cur.copy("COPY email_recipients (email_id, person_id,"
                              " kind) FROM STDIN") as cp:
                    for r in rcpt_rows:
                        cp.write_row(r)
    return len(email_rows)


def main(root):
    conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
    people = PersonCache(conn)
    seen = {r[0] for r in conn.execute(
        "SELECT message_id FROM emails WHERE message_id IS NOT NULL")}
    print(f"resuming: {len(seen)} emails already in DB", flush=True)
    batch, total, skipped, errors = [], 0, 0, 0
    t0 = time.time()
    for folder, path in walk_maildir(root):
        try:
            m = parse_message(path)
        except Exception:
            errors += 1
            continue
        if not m["message_id"] or m["message_id"] in seen:
            skipped += 1
            continue
        seen.add(m["message_id"])
        batch.append((m, folder))
        if len(batch) >= BATCH:
            total += flush(conn, people, batch)
            batch = []
            if (total // BATCH) % 10 == 0:
                rate = total / (time.time() - t0)
                print(f"{total} ingested ({rate:.0f}/s), "
                      f"{skipped} dup/skip, {errors} errors", flush=True)
    if batch:
        total += flush(conn, people, batch)
    print(f"DONE: {total} ingested, {skipped} dup/skip, {errors} errors,"
          f" {len(people.map)} unique addresses,"
          f" {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
