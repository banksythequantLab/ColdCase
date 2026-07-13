# Cold Case — Judge's Guide

An autonomous financial-crimes investigator that uses **CockroachDB as its
persistent memory** to solve the Enron fraud case *blind*, then is scored
against the real convictions. Built for the CockroachDB × AWS Hackathon.

- **Code:** https://github.com/banksythequantLab/ColdCase (MIT)
- **Live dashboard (Cloudflare):** https://coldcase.nota.lawyer
- **AWS-hosted dashboard (S3):** http://coldcase-corpus.s3-website-us-east-1.amazonaws.com

---

## The one-sentence pitch

An autonomous AI investigator that uses **CockroachDB as its persistent brain**
to crack the Enron fraud case *blind* — rediscovering the real convicted
executives with **100% precision@3**. Every hypothesis, finding, and piece of
evidence lives in CockroachDB, so it resumes across sessions and even crashes;
we scored its conclusions against the actual prosecutions.

## Verify the blind investigation yourself (2 minutes)

1. **Zero setup:** open `demo/index.html` — replay a real recorded
   investigation from embedded snapshots (no DB/corpus needed).
2. **Prove it was blind:** `python src/prove_rbac.py` — the agent's DB role is
   *denied* on `judge.poi_labels` (the answer key). Output in
   [`docs/rbac_proof.txt`](rbac_proof.txt).
3. **Score it:** `python src/score_case.py` — precision@3 = 100% vs the 18
   sealed POIs.
4. **Prove memory is decisive:** `python src/ablation.py` — same agent with vs
   without memory (0/18 → 4/18). Chart: [`ablation.png`](ablation.png).
5. **Prove durability:** `python src/restore_verify.py` — restore a case
   snapshot from S3 and verify all evidence SHA-256 hashes.

## Key code (jump straight in)

- Ingestion + person resolution: `src/ingest/parse_maildir.py`
- Embeddings (C-SPANN vector index): `src/ingest/embed_chunks.py`, `sql/schema.sql`
- The 13 agent tools: `src/agent/tools.py`
- Memory resume / session loop: `src/agent/investigator.py` (`resume_context`, `run_session`)
- RBAC "provable blind": `sql/grants.sql`, `src/setup_agent_user.py`
- Managed MCP config: `.mcp.json`
- Evidence backup to S3: `src/agent/backup_case.py`

## Why judges will love this (per criterion)

- **Agentic Memory:** kill the agent mid-investigation, restart, it resumes
  from CockroachDB with zero reprocessing.
- **Technical:** ~1M-vector C-SPANN index + graph + transactional case memory,
  joined in single SQL queries (`hybrid_search`).
- **Impact:** rediscovers real convictions blind; surfaced Kopper via graph
  alone; a real cost case for e-discovery.
- **Production:** RBAC-sealed ground truth, audit-logged MCP, verifiable S3
  restore with chain-of-custody.
- **Creativity:** solving a historical case against real convictions, with an
  honest experiment log including documented failures.

## The honest headline (and the recall defense)

**Using nothing but the raw email corpus, the agent found 4 of the 18 people
who actually pleaded guilty — blind, from zero, with no answer key.** The 14 it
didn't flag are the ones whose guilt rests on testimony, financial filings, and
plea deals that *aren't in the emails* (Fastow, Koenig, Rieker). Recall
measures what's in the corpus; precision measures what's in the agent — and the
agent is conservatively precise (100% precision@3, zero false accusations in
the top tier). The ablation proves the memory is what does it: **0/18 without
memory, 4/18 with it.**

> "You found 4 of 18 — why trust you?" *Because the 4 are the ones we're most
> confident about and can fully justify; we said "I don't know" on the rest
> rather than guess. In e-discovery a false accusation costs millions, so a
> system that knows its limits beats one that guesses. Add the filings and
> testimony and the architecture finds the rest — it just needs the data.*

## Why this is the right demo for "agentic memory"

For most agents, memory is a nice-to-have. For an investigator it *is* the
job: every thread pulled, every contradiction spotted across thousands of
documents, every hunch that pays off sessions later. The Enron corpus is the
perfect adversary because it is real, and it ships with an answer key — 18
documented Persons of Interest (POIs) from the actual prosecution. That lets us
put a hard, quantified number on how well the memory-driven agent performs.

---

## How we score against the five judging criteria

### 1. Agentic Memory Design
CockroachDB is not a cache bolted on the side — it is the agent's brain state.
- **956,398 email-chunk embeddings** + **20,325 per-person behavioural
  "writing-style" centroids** in a distributed **C-SPANN vector index** are the
  agent's semantic recall. (Proof it's real signal: querying Ken Lay's nearest
  neighbours by writing style returns his *actual* secretary and chief of
  staff — the org chart reconstructed from prose alone.)
- **Transactional case memory** — hypotheses, findings, evidence, suspects,
  and an append-only `suspect_events` score-history log — is read at the start
  of every session and written throughout. Kill the agent mid-investigation
  and restart: it resumes exactly where it left off, because the memory was
  never in the process, only in CockroachDB.
- A **363,355-edge communication graph** (pagerank, betweenness) is how the
  agent finds hidden intermediaries.

### 2. Technical Implementation
- Correct use of **pgvector-compatible `VECTOR(384)` columns** and C-SPANN
  indexes; the agent's every "recall" is a real distance query.
- **Bulk ingest** of 500K emails via `COPY`, with resumable, self-healing
  person resolution across 87,505 inconsistent email addresses.
- **13 investigative + memory tools** wired into a local-LLM tool-calling loop;
  evidence rows are SHA-256 hashed on write for chain of custody.
- **Rigorous evaluation** (`src/eval_case.py`): precision-recall curve,
  confusion matrix, and calibration chart against the sealed POI labels.

### 3. Real-World Impact
This is e-discovery / financial-crime detection — a real industry. The results
are quantified, not hand-waved: investigating blind, the agent's **top-3
suspects are all real POIs (100% precision@3)**; it independently surfaced
**Michael Kopper** — Andrew Fastow's lieutenant — purely through the email
graph, a name invisible in the financial data. It also correctly *clears*
high-earning executives when the evidence shows no concealment.

### 4. Production Readiness
- **Provable "blind":** the 18 POI labels live in a separate CockroachDB
  schema (`judge`) on which the agent's service-account role has **zero
  grants** — enforced by RBAC, demonstrable live by having the agent role
  attempt the query and be denied.
- **Managed MCP Server** access is read-only and audit-logged.
- **Evidence preservation:** every session snapshots all case-memory tables to
  Amazon S3 ("the agent preserves its own evidence").
- Least-privilege service account; secrets only in gitignored `.env`.

### 5. Creativity & Originality
An agent that solves a real historical fraud case blind, scored against actual
convictions, is a genuinely novel framing. We also keep an honest **experiment
log** (`docs/EXPERIMENTS.md`) including a documented *failure*: a stance-based
self-critique pass that demoted the real culprits, teaching us that a
perpetrator and a whistleblower look identical in their own outgoing mail —
guilt must be corroborated by *others'* words and hard financials, which is
exactly what the CockroachDB evidence store preserves.

---

## Hackathon requirements checklist

**CockroachDB tools (need ≥2 — we use 3):**
1. **Distributed Vector Indexing (C-SPANN)** — the agent's semantic memory.
2. **Managed MCP Server** — read-only, audit-logged natural-language access to
   the live case (config committed in `.mcp.json`).
3. **Agent Skills / ccloud-equivalent operations** — schema design and the
   session-end backup workflow.

**AWS services (need ≥1 — we use 2):**
- **Amazon S3** — stores the 423MB corpus and every case snapshot.
- **S3 static website hosting** — an AWS-served read-only dashboard.

**Deliverables:** public MIT repo, functional dashboards (live + AWS), and a
demo video (script in `docs/VIDEO_SCRIPT.md`).

---

## Honest current numbers (blind, threshold 0.5)

| metric | value |
|---|---|
| precision@3 | **100%** (Skilling, Lay, Hirko — all POIs) |
| flagged precision | 4 of 7 flagged are real POIs |
| recall | 4 / 18 POIs |
| average precision | 0.32 |

**Known limitations (stated plainly):** recall is the weak axis — the agent
deepens strong cases faster than it broadens to new ones, and it retains two
false positives (Kaminski, a risk officer who *warned against* the deals, and
Lavorato). Both are the "discusses fraud vs commits fraud" problem, which we
show is genuinely hard and document rather than hide. Throughput is bounded by
a shared local GPU, not by CockroachDB, which stays fast throughout. Scaling is
straightforward: the memory layer already runs at cloud scale on CockroachDB;
LLM inference could move to Amazon Bedrock or SageMaker with no change to the
memory architecture.

**Memory-efficiency (why this needs a database, not a context window):** the
corpus is ~239M tokens. The agent reasons over ~27K tokens per session while
its memory spans all 239M - a ~8,800x reduction, ~1,193x larger than a
200K-token context window, and it never re-reads a processed document
(`src/memory_efficiency.py`).

## What makes this more than a demo
The system is honest about what it gets right *and* wrong, grounds every
suspicion in externally-corroborated, hashed evidence stored in CockroachDB,
and survives having its process killed mid-thought. That is the difference
between an agent that *remembers* and a chatbot that forgets.
