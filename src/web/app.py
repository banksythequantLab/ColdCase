"""Cold Case ops dashboard.

Run:  uvicorn app:app --host 127.0.0.1 --port 8060  (from src/web)
Live ingest progress is read from ingest.log (free); DB stats are
on-demand only, because full-table counts burn Request Units on Basic tier.
"""
import os
import re

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
LOG = os.path.join(os.path.dirname(__file__), "..", "..", "ingest.log")
TOTAL_EST = 517000

app = FastAPI(title="Cold Case Ops")
_replay_cache = None


def db():
    return psycopg.connect(os.environ["CRDB_ADMIN_URL"])


def main_case(c):
    """The primary accumulated case (excludes ablation/experiment cases)."""
    r = c.execute(
        "SELECT case_id FROM investigations"
        " WHERE title NOT LIKE 'ablation%%'"
        " ORDER BY created_at LIMIT 1").fetchone()
    return r[0] if r else None


def build_replay():
    """Load timestamped S3 case snapshots into replay frames (cached)."""
    import json
    import boto3
    s3 = boto3.client(
        "s3", region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])
    bucket = os.environ["S3_BUCKET"]
    keys = sorted(o["Key"] for o in s3.list_objects_v2(
        Bucket=bucket, Prefix="backups/").get("Contents", []))
    with db() as c:
        mc = str(main_case(c))
        names = {str(r[0]): r[1] for r in c.execute(
            "SELECT person_id, coalesce(real_name, full_name)"
            " FROM persons WHERE person_id IN"
            " (SELECT person_id FROM suspects)").fetchall()}
    frames = []
    for k in keys:
        d = json.loads(s3.get_object(Bucket=bucket, Key=k)["Body"].read())
        # scope this snapshot to the main investigation only
        hyp_ids = {str(h["hypothesis_id"]) for h in d.get("hypotheses", [])
                   if str(h.get("case_id")) == mc}
        d["hypotheses"] = [h for h in d.get("hypotheses", [])
                           if str(h.get("case_id")) == mc]
        d["findings"] = [f for f in d.get("findings", [])
                         if str(f.get("hypothesis_id")) in hyp_ids]
        find_ids = {str(f["finding_id"]) for f in d["findings"]}
        d["evidence"] = [e for e in d.get("evidence", [])
                         if str(e.get("finding_id")) in find_ids]
        board = sorted([s for s in d.get("suspects", [])
                        if str(s.get("case_id")) == mc],
                       key=lambda x: -float(x["suspicion_score"]))
        frames.append({
            "ts": k.split("case_")[1].replace(".json", ""),
            "hypotheses": [
                {"statement": h.get("statement", ""),
                 "status": h.get("status", "open"),
                 "confidence": round(float(h.get("confidence") or 0), 2)}
                for h in d.get("hypotheses", [])],
            "findings": [
                {"summary": f.get("summary", ""),
                 "method": f.get("method", "")}
                for f in d.get("findings", [])],
            "evidence": [
                {"excerpt": (e.get("excerpt") or "").strip(),
                 "email_id": str(e.get("email_id", ""))[:8]}
                for e in d.get("evidence", []) if (e.get("excerpt") or "").strip()],
            "board": [{"name": names.get(str(s["person_id"]),
                                         str(s["person_id"])[:8]),
                       "score": round(float(s["suspicion_score"]), 2),
                       "why": (s.get("rationale") or "")[:280]}
                      for s in board]})
    return frames


@app.get("/api/replay")
def replay():
    global _replay_cache
    if _replay_cache is None:
        _replay_cache = build_replay()
    return JSONResponse(_replay_cache)


@app.get("/api/progress")
def progress():
    """Parse ingest.log tail — costs zero RUs."""
    out = {"ingested": 0, "rate": 0, "skipped": 0, "errors": 0, "done": False}
    try:
        with open(LOG) as f:
            lines = f.read().strip().splitlines()
    except OSError:
        return JSONResponse(out)
    base = 0
    for ln in lines:
        if m := re.match(r"resuming: (\d+)", ln):
            base = int(m.group(1))
        if m := re.match(r"(\d+) ingested \((\d+)/s\), (\d+) dup/skip,"
                         r" (\d+) errors", ln):
            out.update(ingested=base + int(m.group(1)), rate=int(m.group(2)),
                       skipped=int(m.group(3)), errors=int(m.group(4)))
        if ln.startswith("DONE:"):
            out["done"] = True
            out["ingested"] = base + int(re.search(r"(\d+) ingested", ln)[1])
    out["pct"] = round(100 * out["ingested"] / TOTAL_EST, 1)
    return JSONResponse(out)


@app.get("/api/stats")
def stats():
    """On-demand DB counts (burns RUs — click, don't poll)."""
    with db() as c:
        return JSONResponse({
            "emails": c.execute("SELECT count(*) FROM emails").fetchone()[0],
            "persons": c.execute("SELECT count(*) FROM persons").fetchone()[0],
            "recipient_edges": c.execute(
                "SELECT count(*) FROM email_recipients").fetchone()[0],
        })


@app.get("/api/timeline")
def timeline(person: str = ""):
    """Cross-session audit trail for one suspect: the proof of memory."""
    with db() as c:
        mc = main_case(c)
        if not person:
            # prefer the highest-scored suspect that has clean score history
            person = (c.execute(
                "SELECT s.person_id::STRING FROM suspects s"
                " WHERE s.case_id=%s AND EXISTS (SELECT 1 FROM suspect_events e"
                "   WHERE e.person_id=s.person_id"
                "   AND e.rationale NOT LIKE 'Review/stance%%')"
                " ORDER BY s.suspicion_score DESC LIMIT 1", (mc,)).fetchone()
                or c.execute(
                "SELECT s.person_id::STRING FROM suspects s WHERE s.case_id=%s"
                " ORDER BY s.suspicion_score DESC LIMIT 1", (mc,)).fetchone()
                or [""])[0]
        name = (c.execute("SELECT coalesce(real_name, full_name) FROM persons"
                          " WHERE person_id=%s", (person,)).fetchone()
                or ["?"])[0]
        events = c.execute(
            "SELECT ts, suspicion_score, rationale FROM suspect_events"
            " WHERE person_id=%s AND rationale NOT LIKE 'Review/stance%%'"
            " ORDER BY ts", (person,)).fetchall()
    return JSONResponse({"person_id": person, "name": name,
                         "events": [{"ts": str(e[0])[:19],
                                     "kind": "score " + f"{float(e[1]):.2f}",
                                     "detail": (e[2] or "")[:240]}
                                    for e in events]})


@app.get("/api/graph")
def graph(limit: int = 120):
    """Top communication edges among the most-connected people; suspects
    flagged. One-shot, cached client-side."""
    with db() as c:
        mc = main_case(c)
        nodes = c.execute("""
          SELECT p.person_id::STRING, coalesce(p.real_name, split_part(
                 p.full_name,'@',1)), pp.pagerank,
                 coalesce(s.suspicion_score, -1)
          FROM person_profiles pp JOIN persons p USING (person_id)
          LEFT JOIN suspects s ON s.person_id = p.person_id
             AND s.case_id = %s
          ORDER BY pp.pagerank DESC LIMIT %s""", (mc, limit)).fetchall()
        ids = tuple(n[0] for n in nodes)
        edges = c.execute("""
          SELECT src::STRING, dst::STRING, msg_count FROM comm_edges
          WHERE src = ANY(%s) AND dst = ANY(%s) AND msg_count > 2
          AND src != dst
          ORDER BY msg_count DESC LIMIT 500""",
          (list(ids), list(ids))).fetchall()
    return JSONResponse({
        "nodes": [{"id": n[0], "name": n[1], "rank": float(n[2]),
                   "score": float(n[3])} for n in nodes],
        "edges": [{"source": e[0], "target": e[1], "w": e[2]}
                  for e in edges]})


@app.get("/api/filings")
def filings():
    """SEC filings corpus - the second evidence source in the agent's memory."""
    with db() as c:
        docs = c.execute(
            "SELECT form, filed::STRING, title FROM documents"
            " ORDER BY filed DESC LIMIT 30").fetchall()
        nchunks = c.execute("SELECT count(*) FROM doc_chunks").fetchone()[0]
    return JSONResponse({
        "count": len(docs), "chunks": nchunks,
        "filings": [{"form": r[0], "filed": r[1]} for r in docs]})


@app.get("/api/leads")
def leads():
    """Unexplored high-centrality people not yet on the suspect board -
    the agent's next investigative leads (addresses the recall frontier)."""
    with db() as c:
        mc = main_case(c)
        rows = c.execute("""
          SELECT coalesce(p.real_name, p.full_name), pp.pagerank,
                 pp.betweenness, coalesce(fp.person_id IS NOT NULL, false)
          FROM person_profiles pp
          JOIN persons p USING (person_id)
          LEFT JOIN financial_profiles fp USING (person_id)
          WHERE pp.person_id NOT IN (
              SELECT person_id FROM suspects WHERE case_id=%s)
            AND p.full_name ILIKE '%%@enron.com'
          ORDER BY pp.betweenness DESC LIMIT 8""", (mc,)).fetchall()
    return JSONResponse({"leads": [
        {"name": r[0], "pagerank": round(float(r[1]), 5),
         "betweenness": round(float(r[2]), 5), "has_financials": r[3]}
        for r in rows]})


@app.get("/api/suspects")
def suspects():
    """Live suspect board + case memory counts (cheap queries)."""
    with db() as c:
        mc = main_case(c)
        rows = c.execute("""
          SELECT coalesce(p.real_name, p.full_name), s.suspicion_score,
                 s.rationale, s.updated_at::STRING
          FROM suspects s JOIN persons p USING (person_id)
          WHERE s.case_id = %s
          ORDER BY s.suspicion_score DESC LIMIT 25""", (mc,)).fetchall()
        hyp = c.execute(
            "SELECT status, count(*) FROM hypotheses WHERE case_id=%s"
            " GROUP BY 1", (mc,)).fetchall()
        n_find = c.execute(
            "SELECT count(*) FROM findings f JOIN hypotheses h"
            " USING (hypothesis_id) WHERE h.case_id=%s", (mc,)).fetchone()[0]
        n_ev = c.execute(
            "SELECT count(*) FROM evidence e JOIN findings f"
            " USING (finding_id) JOIN hypotheses h USING (hypothesis_id)"
            " WHERE h.case_id=%s", (mc,)).fetchone()[0]
        n_sess = c.execute(
            "SELECT count(*) FROM agent_sessions WHERE case_id=%s",
            (mc,)).fetchone()[0]
    return JSONResponse({
        "suspects": [{"name": r[0], "score": float(r[1]),
                      "rationale": r[2], "updated": r[3]} for r in rows],
        "hypotheses": {k: v for k, v in hyp},
        "findings": n_find, "evidence": n_ev, "sessions": n_sess})


@app.get("/api/casefile")
def casefile(name: str = "Fastow"):
    """Unified cross-agent case file across all five agents in one CockroachDB
    database, joined on a RESOLVED identity (identity.entities/aliases) rather
    than a raw name -- separating Andrew Fastow from Lea, and Jeffrey Skilling
    from the other Skillings. Cold Case matches on the resolved person_ids."""
    with db() as c:
        ent = c.execute(
            "SELECT e.entity_id, e.canonical FROM identity.entities e "
            "JOIN identity.aliases a ON a.entity_id=e.entity_id "
            "WHERE a.alias ILIKE %s OR e.canonical ILIKE %s LIMIT 1",
            (f"%{name}%", f"%{name}%")).fetchone()
        if ent:
            eid, canonical = ent
            pids = [r[0] for r in c.execute(
                "SELECT person_id FROM identity.aliases "
                "WHERE entity_id=%s AND person_id IS NOT NULL", (eid,)).fetchall()]
            nalias = c.execute("SELECT count(*) FROM identity.aliases "
                               "WHERE entity_id=%s", (eid,)).fetchone()[0]
        else:
            canonical, pids, nalias = name, [], 0
        surname = f"%{canonical.split()[-1]}%"
        agents = {}
        if pids:                      # Cold Case via RESOLVED person_ids (precise)
            cc = c.execute(
                "SELECT concat('suspicion ', round(s.suspicion_score::numeric,2)::string,"
                "' -- ', left(coalesce(s.rationale,''),90)) FROM suspects s "
                "WHERE s.person_id = ANY(%s)", (pids,)).fetchall()
        else:
            cc = c.execute(
                "SELECT concat('suspicion ', round(s.suspicion_score::numeric,2)::string,"
                "' -- ', left(coalesce(s.rationale,''),90)) FROM suspects s "
                "JOIN persons p USING(person_id) WHERE p.full_name ILIKE %s "
                "OR coalesce(p.real_name,'') ILIKE %s", (surname, surname)).fetchall()
        if cc: agents["ColdCase"] = [r[0] for r in cc]
        wit = c.execute(
            "SELECT left(st.claim,120) FROM witness.contradictions cc "
            "JOIN witness.witnesses w ON w.witness_id=cc.witness_id "
            "JOIN witness.statements st ON st.statement_id=cc.statement_id "
            "WHERE w.full_name ILIKE %s", (surname,)).fetchall()
        if wit: agents["Witness"] = [r[0] for r in wit]
        chrn = c.execute(
            "SELECT concat(e.event_date::string,'  ',e.description) FROM chronicle.events e "
            "JOIN chronicle.event_actors a ON a.event_id=e.event_id "
            "WHERE a.actor ILIKE %s AND e.active", (surname,)).fetchall()
        if chrn: agents["Chronicle"] = [r[0] for r in chrn]
        gap = c.execute(
            "SELECT concat(g.target_key,' [',g.status,'] ',coalesce(g.channel_hint,'')) "
            "FROM gaphunter.gaps g WHERE g.subject ILIKE %s", (surname,)).fetchall()
        if gap: agents["GapHunter"] = [r[0] for r in gap]
        held = c.execute("SELECT count(*) FROM hold_docs WHERE held").fetchone()[0]
    return JSONResponse({"name": canonical, "resolved_aliases": nalias,
                         "person_records": len(pids), "agents": agents,
                         "held": held, "coldcase_hit": "ColdCase" in agents})


PAGE = """<!doctype html><html><head><title>Cold Case Ops</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#2a3038;--gold:#f0b429;
--ink:#e9edf2;--mut:#8b949e}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);
font-family:'Inter',system-ui,sans-serif;margin:0 auto;
padding:2.6rem 1.5rem 4rem;max-width:768px;line-height:1.6;
letter-spacing:-.011em;-webkit-font-smoothing:antialiased}
h1{font-size:2rem;font-weight:800;letter-spacing:-.03em;margin:0 0 .15rem;
display:flex;align-items:center;gap:.55rem}
h2{font-size:1.15rem;font-weight:700;letter-spacing:-.02em;color:var(--gold);
margin:2.4rem 0 .35rem;display:flex;align-items:center;gap:.5rem}
h3{font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--mut);margin:1.3rem 0 .5rem}
.sub{color:var(--mut);font-size:.92rem;margin:.15rem 0 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:1.1rem 1.3rem;margin:.85rem 0}
.big{font-size:2.1rem;font-weight:800;letter-spacing:-.03em;
font-variant-numeric:tabular-nums;line-height:1.1}
.bar{background:#21262d;border-radius:6px;height:12px;overflow:hidden;margin:.55rem 0}
.fill{background:linear-gradient(90deg,#e0873a,#f0b429);height:100%;width:0%;
transition:width .6s}
.row{display:flex;gap:.9rem;flex-wrap:wrap}
.row .card{flex:1;min-width:148px;text-align:center}
button{background:#21262d;color:var(--ink);border:1px solid var(--line);
border-radius:8px;padding:.55rem 1.1rem;font-size:.88rem;font-weight:600;
font-family:inherit;cursor:pointer;transition:.15s}
button:hover{border-color:var(--gold);color:var(--gold)}
small{color:var(--mut);font-size:.78rem;letter-spacing:.02em;
text-transform:uppercase;font-weight:600}
.ic{width:1.4rem;height:1.4rem;stroke:var(--gold);fill:none;stroke-width:1.8;
stroke-linecap:round;stroke-linejoin:round;flex:none}
.ic-h2{width:1.15rem;height:1.15rem}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="7"/><path d="M21 21l-5-5"/></symbol>
<symbol id="i-mem" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/><rect x="10" y="10" width="4" height="4" rx="1"/></symbol>
<symbol id="i-net" viewBox="0 0 24 24"><circle cx="5" cy="6" r="2.2"/><circle cx="19" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/><path d="M6.8 7.2l4 9M17.2 7.2l-4 9M7 6h10"/></symbol>
<symbol id="i-scan" viewBox="0 0 24 24"><path d="M3 8V5a2 2 0 0 1 2-2h3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M8 21H5a2 2 0 0 1-2-2v-3"/><circle cx="12" cy="12" r="3.2"/></symbol>
</defs></svg>
<h1><svg class="ic"><use href="#i-search"/></svg>Cold&nbsp;Case</h1>
<p class="sub">Enron corpus &rarr; CockroachDB &middot; agentic-memory
ingestion &middot; live</p>
<a href="/replay" style="display:inline-flex;align-items:center;gap:.4rem;
margin-top:.7rem;background:#21262d;border:1px solid var(--gold);color:var(--gold);
padding:.5rem 1rem;border-radius:8px;font-weight:700;font-size:.9rem;
text-decoration:none">
<svg class="ic ic-h2"><use href="#i-mem"/></svg>Open Memory Replay &rarr;</a>
<div class="card"><div class="big" id="pct">&mdash;</div>
<div class="bar"><div class="fill" id="fill"></div></div>
<small id="detail">loading&hellip;</small></div>
<div class="row">
<div class="card"><small>emails</small><div class="big" id="emails">?</div></div>
<div class="card"><small>people</small><div class="big" id="persons">?</div></div>
<div class="card"><small>graph edges</small><div class="big" id="edges">?</div></div>
</div>
<button onclick="stats()">Refresh DB stats (costs RUs)</button>
<h2><svg class="ic ic-h2"><use href="#i-net"/></svg>Multi-source memory</h2>
<p class="sub">The agent reasons across two evidence sources in one CockroachDB
memory &mdash; email and official SEC filings. The filings carry the
related-party (LJM) disclosures the emails don't.</p>
<div class="row" id="sources"></div>
<h2><svg class="ic ic-h2"><use href="#i-net"/></svg>Unified case file</h2>
<p class="sub">One SQL statement, five agents, one CockroachDB database. Pick a
person and every agent's memory converges &mdash; or a gap is exposed. Fastow is
the tell: the email-driven investigator never flagged him, yet the same query
pulls his contradictions, timeline, and withheld documents from the other agents.</p>
<div id="cfbtns" style="display:flex;gap:.5rem;flex-wrap:wrap;margin:.6rem 0"></div>
<div id="casefile"></div>
<h2><svg class="ic ic-h2"><use href="#i-scan"/></svg>Suspect board</h2>
<p class="sub" id="memstats"></p>
<div id="board"></div>
<h2><svg class="ic ic-h2"><use href="#i-scan"/></svg>Next leads</h2>
<p class="sub">Unexplored high-centrality people not yet flagged - where the
agent would look next. Recall is bounded by evidence, not by candidates.</p>
<div id="leads"></div>
<h2><svg class="ic ic-h2"><use href="#i-mem"/></svg>Memory trail</h2>
<p class="sub">The top suspect's case file, reconstructed across sessions from
CockroachDB &mdash; proof the agent never forgets.</p>
<div id="trail"></div>
<h2><svg class="ic ic-h2"><use href="#i-net"/></svg>Communication network</h2>
<p class="sub">Each dot is an Enron employee among the 60 most central in the
email network; lines connect people who emailed each other (thicker = more
messages). Larger dots have higher PageRank (more influence in the network).
<span style="color:#f0b429">Gold</span> dots are people the agent has flagged as
suspects &mdash; hover any dot for the name and score. This is the same
363,355-edge graph the agent queries to find hidden intermediaries.</p>
<p class="sub" style="margin:.3rem 0">
<span style="color:#f0b429">●</span> flagged suspect (glowing, labelled) ·
<span style="color:#e0873a">●</span> lower-scored suspect ·
<span style="color:#4877b0">●</span> other employee (size = influence) ·
<b>hover</b> a dot to trace only their contacts · <b>drag</b> to pull nodes.</p>
<svg id="graph" width="100%" height="540"
 style="background:radial-gradient(ellipse at center,#101826 0%,#0b0f16 70%);border:1px solid #30363d;border-radius:10px"></svg>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
</body></html>"""

PAGE = PAGE.replace("</body>", """<script>
async function tick(){
  const r = await (await fetch('api/progress')).json();
  document.getElementById('pct').textContent = r.pct + '%' + (r.done?' ✓':'');
  document.getElementById('fill').style.width = Math.min(r.pct,100) + '%';
  document.getElementById('detail').textContent =
    r.ingested.toLocaleString() + ' ingested · ' + r.rate + '/s · ' +
    r.errors + ' errors' + (r.done ? ' · COMPLETE' : '');
}
async function stats(){
  const s = await (await fetch('api/stats')).json();
  document.getElementById('emails').textContent = s.emails.toLocaleString();
  document.getElementById('persons').textContent = s.persons.toLocaleString();
  document.getElementById('edges').textContent =
    s.recipient_edges.toLocaleString();
}
async function board(){
  const b = await (await fetch('api/suspects')).json();
  document.getElementById('memstats').textContent =
    b.sessions + ' sessions · ' +
    Object.entries(b.hypotheses).map(([k,v])=>v+' '+k).join(' · ') +
    ' · ' + b.findings + ' findings · ' + b.evidence + ' evidence rows';
  document.getElementById('board').innerHTML = b.suspects.map(s =>{
    const col = s.score>=0.9?'#f0b429':s.score>=0.5?'#e0873a':'#8b949e';
    return '<div class="card" style="display:flex;gap:1rem;align-items:flex-start">'+
    '<div style="font-size:1.5rem;font-weight:800;color:'+col+
    ';font-variant-numeric:tabular-nums;min-width:2.6rem;letter-spacing:-.03em">'+
    s.score.toFixed(2)+'</div><div><div style="font-weight:700;font-size:1rem;'+
    'letter-spacing:.01em">'+s.name+'</div><div style="color:#8b949e;'+
    'font-size:.86rem;margin-top:.15rem;line-height:1.5">'+
    (s.rationale||'')+'</div></div></div>';}).join('');
}
async function trail(){
  const t = await (await fetch('api/timeline')).json();
  document.getElementById('trail').innerHTML =
    '<div class="card"><b>'+t.name+'</b><br>' +
    t.events.map(e=>'<div style="border-left:2px solid #f0b429;'+
      'padding:.3rem 0 .3rem .8rem;margin:.5rem 0"><small style="color:#8b949e">'+
      e.ts+'</small> &middot; <b style="color:#f0b429">'+e.kind+'</b><br><small>'+
      (e.detail||'')+'</small></div>').join('') + '</div>';
}
async function drawGraph(){
  const g = await (await fetch('api/graph')).json();
  const svg = d3.select('#graph'); const W = svg.node().clientWidth, H = 540;
  svg.selectAll('*').remove();
  const defs = svg.append('defs');
  const fl = defs.append('filter').attr('id','glow').attr('x','-60%')
    .attr('y','-60%').attr('width','220%').attr('height','220%');
  fl.append('feGaussianBlur').attr('stdDeviation','4').attr('result','b');
  const fm = fl.append('feMerge');
  fm.append('feMergeNode').attr('in','b');
  fm.append('feMergeNode').attr('in','SourceGraphic');
  const maxR = d3.max(g.nodes,d=>d.rank)||1;
  const isS = d=>d.score>=0;
  const rOf = d=> isS(d) ? 9+d.score*8 : 3+11*Math.sqrt(d.rank/maxR);
  const adj={}; g.nodes.forEach(n=>adj[n.id]=new Set());
  g.edges.forEach(e=>{const s=e.source.id||e.source,t=e.target.id||e.target;
    if(adj[s])adj[s].add(t); if(adj[t])adj[t].add(s);});
  const root = svg.append('g');
  const sim = d3.forceSimulation(g.nodes)
    .force('link', d3.forceLink(g.edges).id(d=>d.id)
      .distance(d=>62-Math.min(34,Math.log(d.w)*4)).strength(.11))
    .force('charge', d3.forceManyBody().strength(-85))
    .force('collide', d3.forceCollide().radius(d=>rOf(d)+4))
    .force('x', d3.forceX(W/2).strength(.05))
    .force('y', d3.forceY(H/2).strength(.07));
  const link = root.append('g').selectAll('line').data(g.edges).join('line')
    .attr('stroke','#2b3a55')
    .attr('stroke-opacity',d=>Math.min(.65,.12+Math.log(d.w)/12))
    .attr('stroke-width',d=>Math.min(3.5,.4+Math.log(d.w)/2));
  const node = root.append('g').selectAll('circle').data(g.nodes).join('circle')
    .attr('r',rOf)
    .attr('fill',d=>d.score>=0.5?'#f0b429':d.score>=0?'#e0873a':'#4877b0')
    .attr('stroke',d=>isS(d)?'#fff6d5':'#0b0f16')
    .attr('stroke-width',d=>isS(d)?1.6:.6)
    .attr('filter',d=>d.score>=0.5?'url(#glow)':null)
    .style('cursor','pointer')
    .call(d3.drag()
      .on('start',(e,d)=>{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y;})
      .on('drag',(e,d)=>{d.fx=e.x;d.fy=e.y;})
      .on('end',(e,d)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}));
  node.append('title').text(d=>d.name+(isS(d)?' — suspect '+d.score.toFixed(2):' — PageRank '+d.rank.toFixed(4)));
  const topR=[...g.nodes].filter(d=>!isS(d)).sort((a,b)=>b.rank-a.rank).slice(0,6);
  const labeled=g.nodes.filter(d=>isS(d)||topR.includes(d));
  const label = root.append('g').selectAll('text').data(labeled).join('text')
    .text(d=>d.name).attr('text-anchor','middle').attr('pointer-events','none')
    .attr('font-size',d=>isS(d)?12:10).attr('font-weight',d=>isS(d)?700:400)
    .attr('fill',d=>isS(d)?'#ffd75e':'#8b949e')
    .attr('paint-order','stroke').attr('stroke','#0b0f16').attr('stroke-width',3.5);
  node.on('mouseover',(e,d)=>{const k=adj[d.id];
    node.attr('opacity',n=>n.id===d.id||k.has(n.id)?1:.1);
    label.attr('opacity',n=>n.id===d.id||k.has(n.id)?1:.1);
    link.attr('stroke',l=>(l.source.id===d.id||l.target.id===d.id)?'#f0b429':'#2b3a55')
        .attr('stroke-opacity',l=>(l.source.id===d.id||l.target.id===d.id)?.9:.02);})
   .on('mouseout',()=>{node.attr('opacity',1);label.attr('opacity',1);
    link.attr('stroke','#2b3a55').attr('stroke-opacity',l=>Math.min(.65,.12+Math.log(l.w)/12));});
  sim.on('tick',()=>{
    g.nodes.forEach(d=>{const r=rOf(d);d.x=Math.max(r,Math.min(W-r,d.x));d.y=Math.max(r,Math.min(H-r,d.y));});
    link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
        .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('cx',d=>d.x).attr('cy',d=>d.y);
    label.attr('x',d=>d.x).attr('y',d=>d.y-rOf(d)-5);
  });
}
async function leads(){
  const d = await (await fetch('api/leads')).json();
  document.getElementById('leads').innerHTML = d.leads.map(l=>
    '<div class="card" style="display:flex;justify-content:space-between;'+
    'align-items:center;padding:.7rem 1.1rem"><span style="font-weight:600">'+
    l.name.replace('@enron.com','')+'</span><small>betweenness '+
    l.betweenness.toFixed(4)+(l.has_financials?' · exec':'')+'</small></div>'
  ).join('');
}
async function sources(){
  const f = await (await fetch('api/filings')).json();
  document.getElementById('sources').innerHTML =
    '<div class="card"><small>emails</small><div class="big">517,401</div>'+
    '<small style="text-transform:none">956,398 vector memories</small></div>'+
    '<div class="card"><small>SEC filings</small><div class="big">'+f.count+
    '</div><small style="text-transform:none">'+f.chunks.toLocaleString()+
    ' chunks &middot; 10-K, proxy, 8-Ks</small></div>'+
    '<div class="card"><small>one memory</small><div class="big" '+
    'style="color:#58a6ff">CockroachDB</div><small style="text-transform:none">'+
    'joined by vector + SQL</small></div>';
}
const CFPEOPLE=['Skilling','Fastow','Lay','Causey','Kopper'];
function cfBtns(active){
  const box=document.getElementById('cfbtns'); box.innerHTML='';
  CFPEOPLE.forEach(n=>{const b=document.createElement('button');b.textContent=n;
    if(n===active){b.style.borderColor='#f0b429';b.style.color='#f0b429';}
    b.onclick=()=>casefile(n); box.appendChild(b);});
}
async function casefile(name){
  cfBtns(name);
  const d=await (await fetch('api/casefile?name='+encodeURIComponent(name))).json();
  const order=['ColdCase','Witness','Chronicle','GapHunter'];
  const col={ColdCase:'#f85149',Witness:'#3fb950',Chronicle:'#d29922',GapHunter:'#58a6ff'};
  let html='';
  html+='<div style="font-size:.82rem;color:#8b949e;margin:.1rem 0 .6rem">'+
    'entity resolution &rarr; <b style="color:#e6edf3">'+d.name+'</b>'+
    (d.person_records?' &middot; unified '+d.person_records+' person records &amp; '+
     d.resolved_aliases+' aliases into one identity':'')+'</div>';
  if(!d.coldcase_hit){
    html+='<div class="card" style="background:#3a1d1d;border:1px solid #f85149">'+
      '<b style="color:#f77">Cold Case alone missed '+name+'.</b> The same '+
      'one-statement query still builds the case from the other agents below '+
      '&mdash; the entwined CockroachDB memory caught what a single agent could not.</div>';
  }
  for(const ag of order){
    const items=d.agents[ag]||[]; const miss=items.length===0;
    html+='<div class="card" style="border-left:3px solid '+col[ag]+'">'+
      '<div style="font-weight:700;color:'+col[ag]+'">'+ag+
      (miss?' <span style="color:#8b949e;font-weight:400">&mdash; nothing</span>':'')+'</div>'+
      items.map(x=>'<div style="font-size:.86rem;color:#c9d1d9;margin-top:.3rem">'+x+'</div>').join('')+
      '</div>';
  }
  html+='<div class="card" style="border-left:3px solid #bc8cff">'+
    '<div style="font-weight:700;color:#bc8cff">Hold Firewall</div>'+
    '<div style="font-size:.86rem;color:#c9d1d9;margin-top:.3rem">litigation hold '+
    'active on '+d.held+' responsive documents (SERIALIZABLE-protected)</div></div>';
  document.getElementById('casefile').innerHTML=html;
}
tick(); setInterval(tick, 5000);
board(); setInterval(board, 30000);
sources(); casefile('Fastow');
leads(); setInterval(leads, 60000);
trail(); setInterval(trail, 30000);
setTimeout(drawGraph, 800);
</script></body>""")


REPLAY = """<!doctype html><html><head><meta charset="utf-8">
<title>Cold Case — Memory Replay</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#2a3038;--gold:#f0b429;
--ink:#e9edf2;--mut:#8b949e}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);
font-family:'Inter',system-ui,sans-serif;margin:0 auto;
padding:2.6rem 1.5rem 4rem;max-width:768px;line-height:1.6;
letter-spacing:-.011em;-webkit-font-smoothing:antialiased}
h1{font-size:2rem;font-weight:800;letter-spacing:-.03em;margin:0 0 .15rem;
display:flex;align-items:center;gap:.55rem}
h3{font-size:1.05rem;font-weight:700;letter-spacing:-.01em;color:var(--gold);
margin:1.4rem 0 .3rem}
.sub{color:var(--mut);font-size:.92rem;margin:.15rem 0}a{color:#58a6ff;
text-decoration:none}a:hover{text-decoration:underline}
.ic{width:1.4rem;height:1.4rem;stroke:var(--gold);fill:none;stroke-width:1.8;
stroke-linecap:round;stroke-linejoin:round;flex:none}
.counts{display:flex;gap:.75rem;margin:1.1rem 0}
.counts div{background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:.7rem 1rem;flex:1;text-align:center}
.counts b{font-size:1.6rem;font-weight:800;color:var(--gold);display:block;
letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.counts div small,.counts div{font-size:.76rem;color:var(--mut);
text-transform:uppercase;letter-spacing:.05em;font-weight:600}
input[type=range]{width:100%;accent-color:var(--gold);height:6px}
.row{display:flex;align-items:center;gap:.7rem;margin:.35rem 0;
background:var(--panel);border:1px solid var(--line);border-radius:9px;
padding:.55rem .9rem;transition:all .4s}
.row.new{border-color:#3fb950;box-shadow:0 0 0 1px #3fb950}
.bar{height:9px;border-radius:5px;
background:linear-gradient(90deg,#e0873a,#f0b429);transition:width .5s}
.nm{width:158px;font-weight:600;font-size:.9rem}
.sc{width:44px;color:var(--gold);font-weight:800;font-variant-numeric:tabular-nums}
</style></head><body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-mem" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/><rect x="10" y="10" width="4" height="4" rx="1"/></symbol>
</defs></svg>
<h1><svg class="ic"><use href="#i-mem"/></svg>Memory Replay</h1>
<p class="sub"><a href="/">&larr; back to ops dashboard</a></p>
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;
padding:1rem 1.2rem;margin:1rem 0;line-height:1.5">
<b style="color:#f0b429">What am I looking at?</b><br>
Each time the investigator agent finishes a work session, it saves a complete
copy of its memory &mdash; every hypothesis, finding, piece of evidence, and
suspect score &mdash; from CockroachDB to Amazon S3. Each of those saved copies
is one <b>frame</b> below. <b>Drag the slider</b> to move backward and forward
through the investigation's history and watch the agent's thinking evolve:
<ul style="margin:.5rem 0 0 1rem;color:#8b949e">
<li>The <b>counters</b> show how much the agent had discovered by that point in
time (hypotheses it was pursuing, findings it recorded, evidence it collected).</li>
<li>Each <b>bar</b> is one suspect; its length and number are that person's
guilt score <i>at that moment</i>. Watch scores rise as evidence accumulates.</li>
<li>A <b style="color:#3fb950">green-outlined</b> row is a suspect who first
appears in this frame &mdash; a new lead the agent just uncovered.</li>
<li>Hover a row to read the agent's reasoning recorded at that time.</li>
</ul>
This is only possible because the agent's memory <i>persists</i> in
CockroachDB. A stateless chatbot would have nothing to replay.</div>
<div class="counts">
 <div><b id="fi">-</b>frame (session snapshot)</div>
 <div class="tab" data-t="hy"><b id="hy">-</b>hypotheses</div>
 <div class="tab" data-t="fn"><b id="fn">-</b>findings</div>
 <div class="tab" data-t="ev"><b id="ev">-</b>evidence</div>
</div>
<input type="range" id="scrub" min="0" value="0" step="1">
<p class="sub" id="ts"></p>
<h3 style="color:#f0b429;margin:.6rem 0 .2rem">Suspect board</h3>
<div id="board"></div>
<h3 style="color:#f0b429;margin:1rem 0 .2rem" id="dtitle">Hypotheses</h3>
<p class="sub" style="margin:.1rem 0 .5rem">Click the tiles above to switch
between the agent's hypotheses, findings, and the evidence it collected by this
point in the investigation.</p>
<div id="detail"></div>
<style>
.tab{cursor:pointer;transition:border-color .2s}.tab:hover{border-color:#f0b429}
.tab.sel{border-color:#f0b429;box-shadow:0 0 0 1px #f0b429}
.item{background:#161b22;border:1px solid #30363d;border-radius:8px;
padding:.6rem .8rem;margin:.4rem 0}
.item .meta{color:#8b949e;font-size:.8rem;margin-bottom:.2rem}
.badge{display:inline-block;padding:.05rem .5rem;border-radius:10px;
font-size:.72rem;font-weight:700}
.sup{background:#193a24;color:#3fb950}.ref{background:#3a1d1d;color:#f77}
.opn{background:#2b2f36;color:#c9d1d9}
.ev{font-family:ui-monospace,monospace;font-size:.82rem;color:#c9d1d9;
white-space:pre-wrap}
</style>
<script>
let F=[],TAB='hy';
fetch('api/replay').then(r=>r.json()).then(d=>{
  F=d; const s=document.getElementById('scrub');
  s.max=F.length-1; s.value=F.length-1;
  s.oninput=()=>render(+s.value);
  document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
    TAB=t.dataset.t;
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('sel'));
    t.classList.add('sel'); render(+s.value);});
  document.querySelector('.tab[data-t=hy]').classList.add('sel');
  render(F.length-1);
});
function esc(x){return (x||'').replace(/</g,'&lt;').replace(/"/g,'&quot;');}
function render(i){
  const f=F[i], prev=i>0?F[i-1]:{board:[]};
  const pn=new Set(prev.board.map(b=>b.name));
  document.getElementById('fi').textContent=(i+1)+'/'+F.length;
  document.getElementById('hy').textContent=f.hypotheses.length;
  document.getElementById('fn').textContent=f.findings.length;
  document.getElementById('ev').textContent=f.evidence.length;
  document.getElementById('ts').textContent='snapshot '+f.ts;
  document.getElementById('board').innerHTML=f.board.map(b=>
    '<div class="row'+(pn.has(b.name)?'':' new')+'" title="'+esc(b.why)+
    '"><span class="nm">'+b.name+'</span><div class="bar" style="width:'+
    (b.score*120)+'px"></div><span class="sc">'+b.score.toFixed(2)+
    '</span></div>').join('');
  const D=document.getElementById('detail'), T=document.getElementById('dtitle');
  if(TAB=='hy'){T.textContent='Hypotheses ('+f.hypotheses.length+')';
    D.innerHTML=f.hypotheses.map(h=>{
      const c=h.status=='supported'?'sup':h.status=='refuted'?'ref':'opn';
      return '<div class="item"><span class="badge '+c+'">'+h.status+
      ' · '+h.confidence+'</span><div style="margin-top:.3rem">'+
      esc(h.statement)+'</div></div>';}).join('')||'<p class="sub">none yet</p>';
  }else if(TAB=='fn'){T.textContent='Findings ('+f.findings.length+')';
    D.innerHTML=f.findings.map(x=>'<div class="item"><div class="meta">method: '+
      esc(x.method)+'</div>'+esc(x.summary)+'</div>').join('')
      ||'<p class="sub">none yet</p>';
  }else{T.textContent='Evidence ('+f.evidence.length+')';
    D.innerHTML=f.evidence.map(x=>'<div class="item"><div class="meta">'+
      'email '+esc(x.email_id)+' · SHA-256 on record</div><div class="ev">'+
      esc(x.excerpt)+'</div></div>').join('')||'<p class="sub">none yet</p>';}
}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/replay", response_class=HTMLResponse)
def replay_page():
    return REPLAY
