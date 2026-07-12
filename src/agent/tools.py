"""Investigative tools. All reads/writes via the least-privilege agent role
(coldcase_agent) — no access to judge schema. Query embeddings computed
locally (fastembed MiniLM, 384-dim), matching the corpus embeddings.
"""
import hashlib
import json
import os

import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding

load_dotenv()
_model = None


def _embed(text):
    global _model
    if _model is None:
        try:
            sys_path = os.path.join(os.path.dirname(__file__), "..")
            import sys as _s
            _s.path.insert(0, sys_path)
            import gpu_setup
            gpu_setup.enable_cuda_dlls()
            _model = TextEmbedding(os.environ.get(
                "EMBED_MODEL_LOCAL", "sentence-transformers/all-MiniLM-L6-v2"),
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        except Exception:
            _model = TextEmbedding(os.environ.get(
                "EMBED_MODEL_LOCAL", "sentence-transformers/all-MiniLM-L6-v2"))
    v = list(_model.embed([text]))[0]
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def _conn():
    return psycopg.connect(os.environ["CRDB_URL"], autocommit=True)


def semantic_search(query, k=8):
    """Vector search over email chunks (C-SPANN index)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT c.email_id::STRING, left(c.text, 400),"
            " coalesce(p.real_name, p.full_name), e.sent_at::STRING"
            " FROM email_chunks c"
            " JOIN emails e ON e.email_id = c.email_id"
            " LEFT JOIN persons p ON p.person_id = e.sender_id"
            " ORDER BY c.embedding <=> %s::VECTOR LIMIT %s",
            (_embed(query), int(k))).fetchall()
    return [{"email_id": r[0], "excerpt": r[1], "sender": r[2],
             "sent_at": r[3]} for r in rows]


def hybrid_search(query, k=8, graph_weight=0.4):
    """Rank emails by BOTH semantic relevance AND the sender's network
    influence (a single SQL join of the C-SPANN vector index with the
    PageRank graph). Surfaces relevant mail from central actors that pure
    vector search would bury. graph_weight in [0,1] trades the two."""
    gw = max(0.0, min(1.0, float(graph_weight)))
    with _conn() as c:
        rows = c.execute("""
          WITH near AS (
            SELECT ch.email_id, e.sender_id,
                   (ch.embedding <=> %s::VECTOR) AS dist
            FROM email_chunks ch JOIN emails e ON e.email_id = ch.email_id
            ORDER BY dist LIMIT 120),
          hits AS (
            SELECT email_id, sender_id, min(dist) AS dist
            FROM near GROUP BY email_id, sender_id)
          SELECT coalesce(p.real_name, p.full_name),
                 left(e.body, 300), h.email_id::STRING,
                 (1 - h.dist) * (1 - %s) +
                 coalesce(pp.pagerank, 0) * 3000 * %s AS score
          FROM hits h
          JOIN emails e ON e.email_id = h.email_id
          LEFT JOIN persons p ON p.person_id = h.sender_id
          LEFT JOIN person_profiles pp ON pp.person_id = h.sender_id
          ORDER BY score DESC LIMIT %s""",
          (_embed(query), gw, gw, int(k))).fetchall()
    out, seen = [], set()
    for r in rows:
        key = (r[0], (r[1] or "")[:60])
        if key in seen:
            continue
        seen.add(key)
        out.append({"sender": r[0], "excerpt": r[1], "email_id": r[2],
                    "combined_score": round(float(r[3]), 4)})
    return out[:int(k)]


def lookup_person(name_or_email):
    """Find a person by (partial) name or email address, any word order."""
    import re
    toks = [t for t in re.split(r"[\s,.@]+", name_or_email)
            if len(t) > 1][:4]
    if not toks:
        return []
    cond = " AND ".join("(full_name ILIKE %s OR real_name ILIKE %s)"
                        for _ in toks)
    params = [p for t in toks for p in (f"%{t}%", f"%{t}%")]
    with _conn() as c:
        rows = c.execute(
            f"SELECT person_id::STRING, full_name, real_name FROM persons"
            f" WHERE {cond}"
            " ORDER BY (lower(full_name) = lower(%s)) DESC,"
            " (real_name IS NOT NULL) DESC, length(full_name) LIMIT 8",
            (*params, name_or_email)).fetchall()
    return [{"person_id": r[0], "address": r[1], "real_name": r[2]}
            for r in rows]


def read_email(email_id):
    """Read one full email."""
    with _conn() as c:
        r = c.execute(
            "SELECT coalesce(p.real_name, p.full_name), e.sent_at::STRING,"
            " e.subject, left(e.body, 4000) FROM emails e"
            " LEFT JOIN persons p ON p.person_id = e.sender_id"
            " WHERE e.email_id = %s", (email_id,)).fetchone()
    if not r:
        return {"error": "not found"}
    return {"sender": r[0], "sent_at": r[1], "subject": r[2], "body": r[3]}


def financial_outliers(k=12):
    """Employees with anomalous pay/stock, plus loan_advances and email
    volume. QUIET MONEY: big loan_advances or payments with LOW sent_count
    is the hallmark of an actor who hid behind others — investigate them."""
    with _conn() as c:
        rows = c.execute("""
          WITH s AS (SELECT avg(salary) ms, stddev(salary) ss,
                            avg(bonus) mb, stddev(bonus) sb,
                            avg(exercised_stock_options) mx,
                            stddev(exercised_stock_options) sx,
                            avg(total_payments) mt, stddev(total_payments) st
                     FROM financial_profiles)
          SELECT coalesce(p.real_name, p.full_name), p.person_id::STRING,
                 f.salary, f.bonus, f.exercised_stock_options,
                 f.total_payments, f.loan_advances,
                 coalesce(pp.sent_count, 0),
                 greatest(abs(coalesce(f.salary,0)-s.ms)/s.ss,
                          abs(coalesce(f.bonus,0)-s.mb)/s.sb,
                          abs(coalesce(f.exercised_stock_options,0)-s.mx)/s.sx,
                          abs(coalesce(f.total_payments,0)-s.mt)/s.st) z
          FROM financial_profiles f
          JOIN persons p ON p.person_id = f.person_id
          LEFT JOIN person_profiles pp ON pp.person_id = f.person_id, s
          ORDER BY z DESC LIMIT %s""", (int(k),)).fetchall()
    return [{"name": r[0], "person_id": r[1], "salary": r[2], "bonus": r[3],
             "stock_exercised": r[4], "total_payments": r[5],
             "loan_advances": r[6], "sent_emails": r[7],
             "max_zscore": round(float(r[8]), 1),
             "quiet_money": bool((r[6] or 0) > 1_000_000 and (r[7] or 0) < 50)}
            for r in rows]


def graph_neighbors(person_id, k=10):
    """Strongest communication partners of a person."""
    with _conn() as c:
        rows = c.execute("""
          SELECT coalesce(p.real_name, p.full_name), other::STRING, total
          FROM (SELECT dst AS other, msg_count AS total FROM comm_edges
                WHERE src = %s
                UNION ALL
                SELECT src, msg_count FROM comm_edges WHERE dst = %s) t
          JOIN persons p ON p.person_id = t.other
          ORDER BY total DESC LIMIT %s""",
          (person_id, person_id, int(k))).fetchall()
    return [{"name": r[0], "person_id": r[1], "messages": r[2]} for r in rows]


def bridge_nodes(k=10):
    """People with highest betweenness — hidden intermediaries."""
    with _conn() as c:
        rows = c.execute("""
          SELECT coalesce(p.real_name, p.full_name), p.person_id::STRING,
                 pp.betweenness, pp.sent_count, pp.after_hours_ratio
          FROM person_profiles pp JOIN persons p USING (person_id)
          ORDER BY pp.betweenness DESC LIMIT %s""", (int(k),)).fetchall()
    return [{"name": r[0], "person_id": r[1],
             "betweenness": round(float(r[2]), 5), "sent": r[3],
             "after_hours_ratio": round(float(r[4] or 0), 2)} for r in rows]


def similar_people(person_id, k=6):
    """People whose overall writing profile (centroid) is most similar."""
    with _conn() as c:
        rows = c.execute("""
          SELECT coalesce(p2.real_name, p2.full_name), p2.person_id::STRING,
                 (pp2.centroid <=> pp1.centroid)::FLOAT8 dist
          FROM person_profiles pp1, person_profiles pp2
          JOIN persons p2 ON p2.person_id = pp2.person_id
          WHERE pp1.person_id = %s AND pp2.person_id != %s
            AND pp2.centroid IS NOT NULL AND pp1.centroid IS NOT NULL
          ORDER BY dist LIMIT %s""",
          (person_id, person_id, int(k))).fetchall()
    return [{"name": r[0], "person_id": r[1],
             "distance": round(float(r[2]), 4)} for r in rows]


def reputation(surname, k=8):
    """What OTHERS wrote about this person near red-flag topics. Real
    fraudsters don't incriminate themselves; corroboration comes from third
    parties. Returns excerpts from emails NOT sent by matching people that
    mention the surname alongside concealment/partnership/investigation terms."""
    q = (f"{surname} partnership LJM special purpose entity conflict of "
         f"interest investigation concealment self-dealing")
    with _conn() as c:
        rows = c.execute(
            "SELECT left(ch.text, 400),"
            " coalesce(pp.real_name, pp.full_name), e.sent_at::STRING"
            " FROM email_chunks ch"
            " JOIN emails e ON e.email_id = ch.email_id"
            " LEFT JOIN persons pp ON pp.person_id = e.sender_id"
            " WHERE ch.text ILIKE %s"
            " ORDER BY ch.embedding <=> %s::VECTOR LIMIT %s",
            (f"%{surname}%", _embed(q), int(k))).fetchall()
    return [{"excerpt": r[0], "written_by": r[1], "sent_at": r[2]}
            for r in rows]


def timeline(person_id):
    """Monthly email volume for a person — spot bursts and silences."""
    with _conn() as c:
        rows = c.execute("""
          SELECT date_trunc('month', sent_at)::DATE::STRING, count(*)
          FROM emails WHERE sender_id = %s AND sent_at BETWEEN '1998-01-01'
            AND '2002-12-31' GROUP BY 1 ORDER BY 1""",
          (person_id,)).fetchall()
    return [{"month": r[0], "sent": r[1]} for r in rows]


# ===== case-memory writes =====

def _num(v, default=0.5):
    """Coerce model-supplied confidence like '>0.9' or '0.95' to float 0-1."""
    import re
    if isinstance(v, (int, float)):
        return max(0.0, min(1.0, float(v)))
    m = re.search(r"\d*\.?\d+", str(v))
    return max(0.0, min(1.0, float(m.group()))) if m else default


def record_hypothesis(case_id, statement, confidence=0.5):
    """Open a new investigative hypothesis."""
    with _conn() as c:
        hid = c.execute(
            "INSERT INTO hypotheses (case_id, statement, confidence)"
            " VALUES (%s,%s,%s) RETURNING hypothesis_id::STRING",
            (case_id, statement, _num(confidence))).fetchone()[0]
    return {"hypothesis_id": hid}


def update_hypothesis(hypothesis_id, status, confidence):
    """Mark a hypothesis supported/refuted/open with new confidence."""
    with _conn() as c:
        c.execute(
            "UPDATE hypotheses SET status=%s, confidence=%s, updated_at=now()"
            " WHERE hypothesis_id=%s",
            (status, _num(confidence), hypothesis_id))
    return {"ok": True}


def record_finding(hypothesis_id, summary, method, evidence):
    """Record a finding. evidence = list of {email_id, excerpt}."""
    with _conn() as c:
        fid = c.execute(
            "INSERT INTO findings (hypothesis_id, summary, method)"
            " VALUES (%s,%s,%s) RETURNING finding_id::STRING",
            (hypothesis_id, summary, method)).fetchone()[0]
        for ev in (evidence or [])[:6]:
            ex = ev.get("excerpt", "")[:800]
            c.execute(
                "INSERT INTO evidence (finding_id, email_id, excerpt,"
                " excerpt_sha256) VALUES (%s,%s,%s,%s)",
                (fid, ev.get("email_id"), ex,
                 hashlib.sha256(ex.encode()).digest()))
    return {"finding_id": fid}


def update_suspect(case_id, person_id, suspicion_score, rationale):
    """Set/update a suspect's score (0-1) with rationale."""
    with _conn() as c:
        c.execute(
            "UPSERT INTO suspects (case_id, person_id, suspicion_score,"
            " rationale, updated_at) VALUES (%s,%s,%s,%s,now())",
            (case_id, person_id, _num(suspicion_score), rationale[:800]))
        c.execute(
            "INSERT INTO suspect_events (case_id, person_id,"
            " suspicion_score, rationale) VALUES (%s,%s,%s,%s)",
            (case_id, person_id, _num(suspicion_score), rationale[:800]))
    return {"ok": True}
