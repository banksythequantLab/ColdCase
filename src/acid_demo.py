"""Why CockroachDB, not a vector store: concurrent multi-agent writes.

Cold Case's agents (and Deposition Deconstruct's fact-checker fleet) update a
SHARED case memory. When many agents write the same row at once, a naive
read-modify-write silently LOSES updates. CockroachDB's SERIALIZABLE isolation
makes it correct: conflicting transactions are detected and retried, so no
truth is clobbered.

This runs both modes against the live cluster and reports the difference.
Usage: python src/acid_demo.py [num_agents] [increments_each]
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg
from dotenv import load_dotenv

load_dotenv()
URL = os.environ["CRDB_ADMIN_URL"]
AGENTS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
STEPS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
EXPECTED = AGENTS * STEPS


def setup():
    c = psycopg.connect(URL, autocommit=True)
    c.execute("CREATE TABLE IF NOT EXISTS acid_demo"
              " (id INT PRIMARY KEY, corroborations INT8)")
    c.execute("UPSERT INTO acid_demo (id, corroborations) VALUES (1, 0)")
    c.close()


def read_current():
    c = psycopg.connect(URL, autocommit=True)
    v = c.execute("SELECT corroborations FROM acid_demo WHERE id=1").fetchone()[0]
    c.close()
    return v


def naive_agent(_):
    """Read the shared value, then write value+1 in SEPARATE statements -
    the read-modify-write gap that a non-transactional store allows."""
    c = psycopg.connect(URL, autocommit=True)
    for _ in range(STEPS):
        v = c.execute(
            "SELECT corroborations FROM acid_demo WHERE id=1").fetchone()[0]
        time.sleep(0.002)  # the window where another agent reads the same v
        c.execute("UPDATE acid_demo SET corroborations=%s WHERE id=1", (v + 1,))
    c.close()


def serializable_agent(_):
    """Same logic inside a SERIALIZABLE transaction, retrying on conflict."""
    c = psycopg.connect(URL, autocommit=False)
    for _ in range(STEPS):
        while True:
            try:
                with c.transaction():
                    v = c.execute("SELECT corroborations FROM acid_demo"
                                  " WHERE id=1").fetchone()[0]
                    time.sleep(0.002)
                    c.execute("UPDATE acid_demo SET corroborations=%s"
                              " WHERE id=1", (v + 1,))
                break
            except psycopg.errors.SerializationFailure:
                continue  # CockroachDB detected the conflict; retry safely
    c.close()


def run(label, fn):
    c = psycopg.connect(URL, autocommit=True)
    c.execute("UPDATE acid_demo SET corroborations=0 WHERE id=1")
    c.close()
    t = time.time()
    with ThreadPoolExecutor(max_workers=AGENTS) as ex:
        list(ex.map(fn, range(AGENTS)))
    final = read_current()
    dt = time.time() - t
    lost = EXPECTED - final
    print(f"{label:<34} final={final:<5} expected={EXPECTED}"
          f"  lost_updates={lost:<4} ({dt:.1f}s)")
    return lost


if __name__ == "__main__":
    setup()
    print(f"{AGENTS} concurrent agents each record {STEPS} corroborations"
          f" to ONE shared row (expected total {EXPECTED}):\n")
    naive = run("Naive read-modify-write:", naive_agent)
    ser = run("CockroachDB SERIALIZABLE:", serializable_agent)
    print()
    if naive > 0 and ser == 0:
        print(f"Naive mode silently LOST {naive} updates to race conditions.")
        print("SERIALIZABLE isolation lost ZERO - every concurrent write is")
        print("preserved. The memory is a transactional ledger of truths,")
        print("not just an index. This is the CockroachDB difference.")
    else:
        print(f"naive lost={naive}, serializable lost={ser}")
