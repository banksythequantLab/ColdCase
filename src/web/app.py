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


def db():
    return psycopg.connect(os.environ["CRDB_ADMIN_URL"])


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
        if not person:
            person = (c.execute(
                "SELECT s.person_id::STRING FROM suspects s"
                " ORDER BY s.suspicion_score DESC LIMIT 1").fetchone()
                or [""])[0]
        name = (c.execute("SELECT coalesce(real_name, full_name) FROM persons"
                          " WHERE person_id=%s", (person,)).fetchone()
                or ["?"])[0]
        events = c.execute(
            "SELECT ts, suspicion_score, rationale FROM suspect_events"
            " WHERE person_id=%s ORDER BY ts", (person,)).fetchall()
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
        nodes = c.execute("""
          SELECT p.person_id::STRING, coalesce(p.real_name, split_part(
                 p.full_name,'@',1)), pp.pagerank,
                 coalesce(s.suspicion_score, -1)
          FROM person_profiles pp JOIN persons p USING (person_id)
          LEFT JOIN suspects s ON s.person_id = p.person_id
          ORDER BY pp.pagerank DESC LIMIT %s""", (limit,)).fetchall()
        ids = tuple(n[0] for n in nodes)
        edges = c.execute("""
          SELECT src::STRING, dst::STRING, msg_count FROM comm_edges
          WHERE src = ANY(%s) AND dst = ANY(%s) AND msg_count > 2
          ORDER BY msg_count DESC LIMIT 500""",
          (list(ids), list(ids))).fetchall()
    return JSONResponse({
        "nodes": [{"id": n[0], "name": n[1], "rank": float(n[2]),
                   "score": float(n[3])} for n in nodes],
        "edges": [{"s": e[0], "t": e[1], "w": e[2]} for e in edges]})


@app.get("/api/suspects")
def suspects():
    """Live suspect board + case memory counts (cheap queries)."""
    with db() as c:
        rows = c.execute("""
          SELECT coalesce(p.real_name, p.full_name), s.suspicion_score,
                 s.rationale, s.updated_at::STRING
          FROM suspects s JOIN persons p USING (person_id)
          ORDER BY s.suspicion_score DESC LIMIT 25""").fetchall()
        hyp = c.execute(
            "SELECT status, count(*) FROM hypotheses GROUP BY 1").fetchall()
        n_find = c.execute("SELECT count(*) FROM findings").fetchone()[0]
        n_ev = c.execute("SELECT count(*) FROM evidence").fetchone()[0]
        n_sess = c.execute(
            "SELECT count(*) FROM agent_sessions").fetchone()[0]
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
<p class="sub">Top-connected people; <span style="color:#f0b429">gold</span> =
flagged suspects.</p>
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


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
