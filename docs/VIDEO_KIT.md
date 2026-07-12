# Cold Case — Turnkey Video Kit (target 2:55)

Everything you need to record the 3-minute submission video: word-for-word
narration (left) synced to exact on-screen actions (right). Read the narration
at a calm pace; each block is timed. Record at 1920×1080.

**Before you start:** open three browser tabs —
1. `https://coldcase.savagealgo.com` (dashboard)
2. `https://coldcase.savagealgo.com/replay` (memory replay)
3. a terminal in `B:\ColdCase`
Have `python src/agent/investigator.py` ready to paste, and `python
src/score_case.py` ready. Full-screen the browser, hide bookmarks.

---

### 0:00–0:22 · The hook
**Narration:**
> "The Enron email corpus exists because of a fraud investigation — half a
> million real emails from the executives who were prosecuted. We gave an AI
> agent all of it, hid the list of who was actually convicted, and asked it to
> solve the case. This is Cold Case — an autonomous investigator whose memory
> lives in CockroachDB."

**Screen:** Dashboard tab (title + suspect board visible). Slow scroll down
past the "Cold Case" wordmark to the suspect board.

### 0:22–0:52 · Memory at scale
**Narration:**
> "The agent's memory is CockroachDB. Every email is chunked and embedded —
> nearly a million vectors in a distributed C-SPANN index — alongside a
> 363-thousand-edge communication graph. Watch: this network is what the agent
> queries to find hidden intermediaries."

**Screen:** Scroll to the Communication network graph. Hover a gold suspect
node so its contacts light up gold and the rest fade. Move to a second suspect.

### 0:52–1:35 · The investigation loop
**Narration:**
> "Each session, the agent resumes its memory, picks a lead, and works it —
> searching emails, reading them, checking financial outliers and who's talking
> about whom. Everything it concludes is written back to CockroachDB as
> hypotheses, findings, and evidence — every excerpt hashed for chain of
> custody."

**Screen:** Terminal. Run `python src/agent/investigator.py`. Let the tool-call
trace scroll for a few seconds (financial_outliers → semantic_search →
read_email → record_finding → update_suspect).

### 1:35–2:05 · Persistence — the core requirement
**Narration:**
> "Here's the whole point. I'll kill it mid-investigation." *(Ctrl-C)* "And
> restart it." *(re-run)* "It prints 'resuming case' and continues exactly
> where it left off — because the memory was never in the process. It was
> always in CockroachDB. Nothing lost."

**Screen:** Ctrl-C the running agent. Re-run the same command. Point cursor at
the `resuming case…` line.

### 2:05–2:35 · The blind reveal
**Narration:**
> "After a run of sessions, here's its suspect board — and now the reveal.
> Its top suspects are Skilling, Lay, Hirko, and Kopper: all real Enron
> convictions. The answer key it's scored against lives in a database schema
> the agent's own account is forbidden to read."

**Screen:** Terminal: run `python src/score_case.py` — show `precision@3 = 100%`.
Then run: `psql "$CRDB_URL" -c "SELECT * FROM judge.poi_labels LIMIT 1"` to show
the **permission denied** error (agent role can't read ground truth).

### 2:35–2:55 · Memory replay + close
**Narration:**
> "And because the memory persists, you can replay the entire investigation —
> watch suspects appear and scores climb as evidence accumulates. Agents that
> think, act, and remember — reliably, at any scale. That's what makes an
> investigator instead of a chatbot."

**Screen:** Replay tab. Drag the slider from left to right so the board fills
in and Kopper appears. End on the architecture diagram (open `docs/architecture.svg`)
with the GitHub URL on screen.

---

## One-take fallback (no terminal)
If live terminal is risky, use the **offline demo** (`demo/index.html`) for the
persistence/replay story: scrub the slider, click the Hypotheses/Findings/
Evidence tiles to show real content. Narrate the same beats. It never fails on
camera because there's no backend.

## Shot checklist
- [ ] Dashboard wordmark + suspect board (100% top-3)
- [ ] Communication graph hover-to-trace
- [ ] investigator.py tool-call trace
- [ ] Ctrl-C then resume ("resuming case…")
- [ ] score_case.py → precision@3 100%
- [ ] judge.poi_labels permission-denied
- [ ] replay slider filling the board
- [ ] architecture diagram + GitHub URL

## Post
Upload to YouTube **unlisted or public** (Devpost requires a public/unlisted
link). Title: "Cold Case — an AI investigator with CockroachDB memory solves
Enron blind." Put the GitHub + live-dashboard links in the description.
