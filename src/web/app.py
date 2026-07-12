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
        names = {str(r[0]): r[1] for r in c.execute(
            "SELECT person_id, coalesce(real_name, full_name)"
            " FROM persons WHERE person_id IN"
            " (SELECT person_id FROM suspects)").fetchall()}
    frames = []
    for k in keys:
        d = json.loads(s3.get_object(Bucket=bucket, Key=k)["Body"].read())
        board = sorted(d.get("suspects", []),
                       key=lambda x: -float(x["suspicion_score"]))
        frames.append({
            "ts": k.split("case_")[1].replace(".json", ""),
            "hypotheses": len(d.get("hypotheses", [])),
            "findings": len(d.get("findings", [])),
            "evidence": len(d.get("evidence", [])),
            "board": [{"name": names.get(str(s["person_id"]),
                                         str(s["person_id"])[:8]),
                       "score": round(float(s["suspicion_score"]), 2),
                       "why": (s.get("rationale") or "")[:200]}
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
            person = (c.execute(
                "SELECT s.person_id::STRING FROM suspects s"
                " WHERE s.case_id=%s ORDER BY s.suspicion_score DESC LIMIT 1",
                (mc,)).fetchone() or [""])[0]
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


PAGE = """<!doctype html><html><head><title>Cold Case Ops</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0d1117;color:#e6edf3;font-family:system-ui;margin:0;
padding:2rem;max-width:720px;margin:auto}
h1{color:#f0b429}.sub{color:#8b949e}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;
padding:1.2rem;margin:1rem 0}
.big{font-size:2.4rem;font-weight:700}
.bar{background:#21262d;border-radius:6px;height:14px;overflow:hidden}
.fill{background:#f0b429;height:100%;width:0%;transition:width .5s}
.row{display:flex;gap:1rem;flex-wrap:wrap}.row .card{flex:1;min-width:150px}
button{background:#238636;color:#fff;border:0;border-radius:6px;
padding:.6rem 1.2rem;font-size:1rem;cursor:pointer}
small{color:#8b949e}
</style></head><body>
<h1>&#128374; Cold Case</h1>
<p class="sub">Enron corpus &rarr; CockroachDB &middot; agentic memory
ingestion &middot; live</p>
<div class="card"><div class="big" id="pct">&mdash;</div>
<div class="bar"><div class="fill" id="fill"></div></div>
<small id="detail">loading&hellip;</small></div>
<div class="row">
<div class="card"><small>emails</small><div class="big" id="emails">?</div></div>
<div class="card"><small>people</small><div class="big" id="persons">?</div></div>
<div class="card"><small>graph edges</small><div class="big" id="edges">?</div></div>
</div>
<button onclick="stats()">Refresh DB stats (costs RUs)</button>
<h2 style="color:#f0b429;margin-top:2rem">&#128373; Suspect board</h2>
<p class="sub" id="memstats"></p>
<div id="board"></div>
<h2 style="color:#f0b429;margin-top:2rem">&#129504; Memory trail</h2>
<p class="sub">The top suspect's case file, reconstructed across sessions from
CockroachDB &mdash; proof the agent never forgets.</p>
<div id="trail"></div>
<h2 style="color:#f0b429;margin-top:2rem">&#128225; Communication network</h2>
<p class="sub">Each dot is an Enron employee among the 60 most central in the
email network; lines connect people who emailed each other (thicker = more
messages). Larger dots have higher PageRank (more influence in the network).
<span style="color:#f0b429">Gold</span> dots are people the agent has flagged as
suspects &mdash; hover any dot for the name and score. This is the same
363,355-edge graph the agent queries to find hidden intermediaries.</p>
<svg id="graph" width="100%" height="460"
 style="background:#0b0f16;border:1px solid #30363d;border-radius:10px"></svg>
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
  document.getElementById('board').innerHTML = b.suspects.map(s =>
    '<div class="card"><b>' + s.name + '</b>' +
    '<span style="float:right;color:#f0b429;font-size:1.3rem">' +
    s.score.toFixed(2) + '</span><br><small>' +
    (s.rationale||'') + '</small></div>').join('');
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
  const svg = d3.select('#graph'), W = svg.node().clientWidth, H = 460;
  svg.selectAll('*').remove();
  const sim = d3.forceSimulation(g.nodes)
    .force('link', d3.forceLink(g.edges).id(d=>d.id).distance(40).strength(.3))
    .force('charge', d3.forceManyBody().strength(-30))
    .force('center', d3.forceCenter(W/2, H/2));
  const link = svg.append('g').attr('stroke','#30363d').attr('stroke-opacity',.5)
    .selectAll('line').data(g.edges).join('line')
    .attr('stroke-width', d=>Math.min(3, Math.log(d.w)));
  const node = svg.append('g').selectAll('circle').data(g.nodes).join('circle')
    .attr('r', d=> d.score>=0 ? 7 : 3+d.rank*400)
    .attr('fill', d=> d.score>=0.5 ? '#f0b429' : d.score>=0 ? '#d97706' : '#3b5573')
    .attr('stroke','#0b0f16');
  node.append('title').text(d=> d.name + (d.score>=0?' (suspect '+d.score.toFixed(2)+')':''));
  sim.on('tick', ()=>{
    link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
        .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('cx',d=>Math.max(6,Math.min(W-6,d.x)))
        .attr('cy',d=>Math.max(6,Math.min(H-6,d.y)));
  });
}
tick(); setInterval(tick, 5000);
board(); setInterval(board, 30000);
trail(); setInterval(trail, 30000);
setTimeout(drawGraph, 800);
</script></body>""")


REPLAY = """<!doctype html><html><head><meta charset="utf-8">
<title>Cold Case — Memory Replay</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0d1117;color:#e6edf3;font-family:system-ui;margin:0;
padding:2rem;max-width:760px;margin:auto}
h1{color:#f0b429}.sub{color:#8b949e}a{color:#58a6ff}
.counts{display:flex;gap:1rem;margin:1rem 0}
.counts div{background:#161b22;border:1px solid #30363d;border-radius:8px;
padding:.6rem 1rem;flex:1;text-align:center}
.counts b{font-size:1.5rem;color:#f0b429;display:block}
input[type=range]{width:100%;accent-color:#f0b429}
.row{display:flex;align-items:center;gap:.6rem;margin:.35rem 0;
background:#161b22;border:1px solid #30363d;border-radius:8px;padding:.5rem .8rem;
transition:all .4s}
.row.new{border-color:#3fb950;box-shadow:0 0 0 1px #3fb950}
.bar{height:10px;border-radius:5px;background:#f0b429;transition:width .5s}
.nm{width:150px;font-weight:600}.sc{width:44px;color:#f0b429;font-weight:700}
</style></head><body>
<h1>&#129504; Memory Replay</h1>
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
 <div><b id="hy">-</b>hypotheses</div>
 <div><b id="fn">-</b>findings</div><div><b id="ev">-</b>evidence</div>
</div>
<input type="range" id="scrub" min="0" value="0" step="1">
<p class="sub" id="ts"></p>
<div id="board"></div>
<script>
let F=[];
fetch('api/replay').then(r=>r.json()).then(d=>{
  F=d; const s=document.getElementById('scrub');
  s.max=F.length-1; s.value=F.length-1;
  s.oninput=()=>render(+s.value); render(F.length-1);
});
function render(i){
  const f=F[i], prev=i>0?F[i-1]:{board:[]};
  const pn=new Set(prev.board.map(b=>b.name));
  document.getElementById('fi').textContent=(i+1)+'/'+F.length;
  document.getElementById('hy').textContent=f.hypotheses;
  document.getElementById('fn').textContent=f.findings;
  document.getElementById('ev').textContent=f.evidence;
  document.getElementById('ts').textContent='snapshot '+f.ts;
  document.getElementById('board').innerHTML=f.board.map(b=>
    '<div class="row'+(pn.has(b.name)?'':' new')+'" title="'+
    (b.why||'').replace(/"/g,'')+'"><span class="nm">'+b.name+
    '</span><div class="bar" style="width:'+(b.score*120)+'px"></div>'+
    '<span class="sc">'+b.score.toFixed(2)+'</span></div>').join('');
}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/replay", response_class=HTMLResponse)
def replay_page():
    return REPLAY
