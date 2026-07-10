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
tick(); setInterval(tick, 5000);
</script></body>""")


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
