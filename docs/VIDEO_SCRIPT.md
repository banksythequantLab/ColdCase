# Cold Case — 3-Minute Demo Video Script

Target: < 3:00. Screen recording + voiceover. Must show the CockroachDB memory
layer at work (hackathon requirement).

---

**[0:00–0:20] The hook**
> "The Enron email corpus exists because of a fraud investigation. Half a
> million real emails. A hundred and fifty executives. Eighteen of them were
> named Persons of Interest by the actual prosecution. We gave an AI agent all
> of it — and hid the answer key. Then we asked it to solve the case."

Screen: title card → the corpus in S3 → row counts in CockroachDB.

**[0:20–0:50] Memory at scale**
> "The agent's memory is CockroachDB. Every email is chunked and embedded —
> nearly a million vectors in a distributed C-SPANN index. Watch: search for
> 'off-balance-sheet entities hiding debt' — no keywords, pure meaning."

Screen: run `semantic_search`, show real Enron off-balance-sheet emails
returned. Then show the org-chart reconstruction: Ken Lay's nearest neighbors
by writing style = his real secretary + chief of staff.

**[0:50–1:30] The agent investigates**
> "Each session, the agent resumes its memory, picks a lead, and works it —
> financial outliers, the communication graph, reading the actual emails.
> Everything it concludes is written back to CockroachDB as hypotheses,
> findings, and evidence — every excerpt hashed for chain of custody."

Screen: launch `investigator.py`, show the tool-call trace scrolling
(financial_outliers → record_hypothesis → semantic_search → read_email →
record_finding → update_suspect). Show rows appearing in the DB.

**[1:30–2:00] Persistence — the core requirement**
> "This is the whole point: kill it mid-investigation."

Screen: Ctrl-C the process. Restart it.

> "It resumes exactly where it left off — because the memory was never in the
> process. It was always in CockroachDB. Nothing lost."

Screen: agent prints "resuming case…" and continues.

**[2:00–2:35] The reveal**
> "After a dozen sessions, blind, here's its suspect board."

Screen: the dashboard suspect board, then run `score_case.py` (admin-only —
the agent can't read this).

> "Its two highest-conviction suspects: Jeffrey Skilling and Kenneth Lay — the
> two most famous Enron convictions — each backed by evidence it found itself.
> The labels it's being scored against? In a schema the agent has zero
> permission to read. It solved this blind."

Screen: show the RBAC denial — agent role querying `judge.poi_labels` → access
denied.

**[2:35–3:00] Close**
> "Agents that think, act, and remember — reliably, at any scale. The thinking
> and acting run locally. The remembering runs on CockroachDB. That's what
> makes an agent an investigator instead of a chatbot."

Screen: architecture diagram → GitHub + live URL → CockroachDB x AWS logos.

---

## Shot checklist
- [ ] S3 bucket contents (corpus + report)
- [ ] CockroachDB row counts / vector index
- [ ] semantic_search live result
- [ ] org-chart similarity result
- [ ] investigator.py tool trace
- [ ] kill + resume
- [ ] dashboard suspect board
- [ ] score_case.py output
- [ ] RBAC denial on judge schema
- [ ] MCP query in Claude Code ("who is the top suspect?")
