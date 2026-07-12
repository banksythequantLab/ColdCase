# Cold Case — offline demo (zero setup)

Watch a real AI investigation replay in under a minute, with **no database,
server, corpus, or dependencies**.

## Run it

**Option A — double-click.** Open `index.html` in any browser.

**Option B — local server** (if your browser blocks local file scripts):

```bash
cd demo
python -m http.server 8000
# then open http://localhost:8000
```

## What you're looking at

`data.js` contains **real snapshots** of the investigator agent's memory,
captured from CockroachDB after each work session as it investigated the Enron
fraud corpus (517,401 emails) *blind* — with the list of convicted executives
sealed in a database schema the agent could not read.

Drag the slider to replay the investigation. Watch the suspect board grow, the
hypotheses flip from `open` to `supported`/`refuted`, and the evidence
accumulate. The agent's top suspects — **Skilling, Lay, Hirko, Kopper** — are
all real Enron convictions it identified on its own.

This is a static export. The full live system (agent loop, vector search over
956K embeddings, communication graph, managed MCP access) is in the parent
repo; live dashboards are linked from the main README.
