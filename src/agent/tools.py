"""Investigative tools the agent can call. All reads via the agent service
account (no judge schema access). Status: SKELETON — untested. Week 2-3.
"""
import hashlib
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def _conn():
    return psycopg.connect(os.environ["CRDB_URL"])  # agent role, least privilege


def semantic_search(query_embedding, k=10):
    """Vector search over email_chunks via C-SPANN index."""
    sql = """SELECT chunk_id, email_id, text,
                    embedding <=> %s::VECTOR AS dist
             FROM email_chunks ORDER BY dist LIMIT %s"""
    with _conn() as c:
        return c.execute(sql, (query_embedding, k)).fetchall()


def similar_people(person_id, k=5):
    sql = """SELECT p2.person_id, p2.centroid <=> p1.centroid AS dist
             FROM person_profiles p1, person_profiles p2
             WHERE p1.person_id = %s AND p2.person_id != %s
             ORDER BY dist LIMIT %s"""
    with _conn() as c:
        return c.execute(sql, (person_id, person_id, k)).fetchall()


def financial_outliers():
    """Z-scores across financial features; returns top anomalies."""
    # TODO Week 3: per-feature z-score SQL over financial_profiles
    raise NotImplementedError


def record_finding(hypothesis_id, summary, method, evidence_rows):
    """Insert finding + evidence with SHA-256 excerpt hashes, one txn."""
    with _conn() as c:
        with c.transaction():
            fid = c.execute(
                "INSERT INTO findings (hypothesis_id, summary, method)"
                " VALUES (%s,%s,%s) RETURNING finding_id",
                (hypothesis_id, summary, method)).fetchone()[0]
            for email_id, excerpt in evidence_rows:
                c.execute(
                    "INSERT INTO evidence (finding_id, email_id, excerpt,"
                    " excerpt_sha256) VALUES (%s,%s,%s,%s)",
                    (fid, email_id, excerpt,
                     hashlib.sha256(excerpt.encode()).digest()))
    return fid


def update_suspect(case_id, person_id, score, rationale):
    with _conn() as c:
        c.execute(
            "UPSERT INTO suspects (case_id, person_id, suspicion_score,"
            " rationale, updated_at) VALUES (%s,%s,%s,%s,now())",
            (case_id, person_id, score, rationale))
