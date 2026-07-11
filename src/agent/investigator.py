"""Cold Case investigator — multi-session agent with CockroachDB memory.

Usage:
  python src/agent/investigator.py --new-case "Enron"
  python src/agent/investigator.py            (resumes latest open case)

Brain: local Ollama (OLLAMA_URL/AGENT_MODEL). Memory: CockroachDB via the
least-privilege agent role. Kill it anytime — nothing is lost.
"""
import inspect
import json
import os
import sys
import time

import psycopg
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(__file__))
import tools as T

load_dotenv()
MAX_CALLS = int(os.environ.get("MAX_TOOL_CALLS_PER_SESSION", 40))

TOOL_FNS = [T.semantic_search, T.lookup_person, T.read_email,
            T.financial_outliers, T.graph_neighbors, T.bridge_nodes,
            T.similar_people, T.timeline, T.record_hypothesis,
            T.update_hypothesis, T.record_finding, T.update_suspect]


def schema_for(fn):
    sig = inspect.signature(fn)
    props, req = {}, []
    for name, p in sig.parameters.items():
        t = "integer" if isinstance(p.default, int) else \
            "number" if isinstance(p.default, float) else \
            "array" if name == "evidence" else "string"
        props[name] = {"type": t}
        if p.default is inspect.Parameter.empty:
            req.append(name)
    return {"type": "function", "function": {
        "name": fn.__name__, "description": fn.__doc__.strip(),
        "parameters": {"type": "object", "properties": props,
                       "required": req}}}


SYSTEM = """You are a financial-crimes investigator examining the email and
financial records of Enron Corporation (~500,000 emails, 144 executives'
financials). You do NOT know who, if anyone, committed fraud. Your job:
find suspicious patterns and build an evidence-backed suspect list.

Method, each session:
1. Review your case memory (provided below): open hypotheses, prior findings,
   current suspects.
2. Pick ONE line of investigation and pursue it with tools (search emails,
   read them, check financial outliers, communication graph, timelines).
3. PERSIST what you learn: record_hypothesis for new leads,
   record_finding (with evidence email_ids + verbatim excerpts) for results,
   update_hypothesis when supported/refuted, update_suspect with a 0-1
   score and rationale whenever your view of a person changes.
4. Cite evidence. Never score a suspect without at least one recorded
   finding. Scores: 0.9+ = strong documentary evidence of fraud;
   0.5 = suspicious pattern worth pursuing; below 0.2 = likely clean.

Be skeptical: high pay alone is not fraud. Look for: off-book entities,
special purpose vehicles, hidden debt, backdated deals, insider selling
before bad news, pressure on accountants, destroyed documents.

Three hard rules learned from prior casework:
- STANCE CHECK: read the author's position in every evidence excerpt.
  People who OBJECT to, warn about, or analyze risky structures are
  witnesses/whistleblowers, NOT suspects. Discussing fraud != committing it.
  If current evidence for a suspect is all analysis/warnings, LOWER their
  score and record why.
- CONCEALMENT GATE: never set suspicion_score above 0.6 unless a recorded
  finding shows concealment or deception (hiding debt, misleading
  statements, self-dealing, pressure to stay silent). Compensation size
  alone caps a score at 0.4.
- QUIET-MONEY RULE: the best-hidden actors avoid email. In
  financial_outliers, any row with quiet_money=true (large loan_advances,
  few sent emails) is a PRIORITY lead — investigate them through OTHER
  people's emails (semantic_search their surname + 'partnership'/'LJM'/
  'special purpose entity'), not their own mailbox.
- BREADTH OVER DEPTH: Skilling, Lay, and Hirko are already well-established
  in your memory — do NOT re-investigate them. Your goal THIS session is to
  find a NEW guilty party not yet on the board. Call financial_outliers with
  k=20, pick someone with score 0 in your memory, and pursue them. Names
  worth checking via email if unexplored: Causey, Delainey, Koenig, Rieker,
  Fastow (via LJM), Kopper, Glisan, Calger. Add them only with real evidence
  of concealment/self-dealing, not mere association.
When you have used your tool budget or finished the line of inquiry,
write a 3-5 sentence session summary as your final plain-text reply."""


def resume_context(conn, case_id):
    hyps = conn.execute(
        "SELECT hypothesis_id::STRING, statement, confidence, status"
        " FROM hypotheses WHERE case_id=%s ORDER BY updated_at DESC"
        " LIMIT 12", (case_id,)).fetchall()
    sess = conn.execute(
        "SELECT summary FROM agent_sessions WHERE case_id=%s AND summary"
        " IS NOT NULL ORDER BY started_at DESC LIMIT 3",
        (case_id,)).fetchall()
    susp = conn.execute(
        "SELECT coalesce(p.real_name, p.full_name), s.person_id::STRING,"
        " s.suspicion_score, s.rationale FROM suspects s"
        " JOIN persons p USING (person_id) WHERE s.case_id=%s"
        " ORDER BY s.suspicion_score DESC LIMIT 10", (case_id,)).fetchall()
    return json.dumps({
        "case_id": str(case_id),
        "open_hypotheses": [{"id": h[0], "statement": h[1],
                             "confidence": float(h[2]), "status": h[3]}
                            for h in hyps],
        "recent_session_summaries": [s[0] for s in sess],
        "current_suspects": [{"name": s[0], "person_id": s[1],
                              "score": float(s[2]), "why": s[3]}
                             for s in susp]}, indent=1)


def run_session(case_id, conn):
    client = OpenAI(base_url=os.environ["OLLAMA_URL"], api_key="ollama")
    model = os.environ["AGENT_MODEL"]
    sid = conn.execute(
        "INSERT INTO agent_sessions (case_id) VALUES (%s)"
        " RETURNING session_id", (case_id,)).fetchone()[0]
    dispatch = {f.__name__: f for f in TOOL_FNS}
    schemas = [schema_for(f) for f in TOOL_FNS]
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content":
             "CASE MEMORY:\n" + resume_context(conn, case_id) +
             f"\n\nBegin session. Tool budget: {MAX_CALLS} calls."}]
    calls = 0
    while calls < MAX_CALLS:
        r = client.chat.completions.create(
            model=model, messages=msgs, tools=schemas, max_tokens=1500)
        m = r.choices[0].message
        msgs.append({"role": "assistant", "content": m.content,
                     "tool_calls": [tc.model_dump() for tc in
                                    (m.tool_calls or [])] or None})
        if not m.tool_calls:
            summary = (m.content or "").strip()[:1500]
            break
        for tc in m.tool_calls:
            calls += 1
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
                if "case_id" in args or name in ("record_hypothesis",
                                                 "update_suspect"):
                    args["case_id"] = str(case_id)
                out = dispatch[name](**args)
            except Exception as e:
                out = {"error": str(e)[:300]}
            print(f"[{calls}] {name}({tc.function.arguments[:110]})",
                  flush=True)
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": json.dumps(out, default=str)[:6000]})
    else:
        summary = "(tool budget exhausted before summary)"
    conn.execute("UPDATE agent_sessions SET ended_at=now(), summary=%s"
                 " WHERE session_id=%s", (summary, sid))
    print("\nSESSION SUMMARY:\n" + summary)
    try:  # preserve evidence off-cluster at session end
        import backup_case
        backup_case.snapshot()
    except Exception as e:
        print(f"(backup skipped: {str(e)[:120]})")


def main():
    conn = psycopg.connect(os.environ["CRDB_URL"], autocommit=True)
    if len(sys.argv) > 2 and sys.argv[1] == "--new-case":
        case_id = conn.execute(
            "INSERT INTO investigations (title) VALUES (%s)"
            " RETURNING case_id", (sys.argv[2],)).fetchone()[0]
        print(f"new case: {case_id}")
    else:
        row = conn.execute(
            "SELECT case_id FROM investigations WHERE status='open'"
            " ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:
            sys.exit("no open case — use --new-case \"title\"")
        case_id = row[0]
        print(f"resuming case: {case_id}")
    t0 = time.time()
    run_session(case_id, conn)
    print(f"session complete in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
