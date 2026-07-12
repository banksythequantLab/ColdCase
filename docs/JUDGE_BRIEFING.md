# Cold Case - Project Briefing for Evaluation

*This document is written for an AI reviewer asked to critique the project and
suggest improvements. It is a complete, self-contained account: you do not need
to see the code to evaluate it. It is deliberately honest about weaknesses.*

**Links**
- Code (MIT): https://github.com/banksythequantLab/ColdCase
- Live dashboard: https://coldcase.savagealgo.com
- Memory replay: https://coldcase.savagealgo.com/replay
- AWS-hosted board: http://coldcase-corpus.s3-website-us-east-1.amazonaws.com
- Zero-setup offline demo: `demo/index.html` in the repo
- Full criterion-mapped judge guide: `docs/FOR_JUDGES.md`
- Experiment log (incl. failures): `docs/EXPERIMENTS.md`

---

## 1. What was built, in one paragraph

Cold Case is an autonomous financial-crimes investigator whose persistent memory
lives in CockroachDB. It was given the real Enron email corpus (517,401 emails
from ~150 executives) plus the Enron financial dataset (144 executives, 18
labelled "Persons of Interest" from the actual prosecution). The 18 POI labels
are sealed in a separate database schema the agent's DB role has zero permission
to read. Across many autonomous "sessions", a local LLM agent investigates the
corpus - searching emails semantically, reading them, analysing financial
outliers and the communication graph - and writes every hypothesis, finding,
piece of evidence, and suspect score back to CockroachDB. Because all state
lives in the database, the agent resumes seamlessly across sessions and even
across process crashes. The project is submitted to the "CockroachDB x AWS
Hackathon: Build with Agentic Memory."

## 2. The headline result (blind)

Investigating with no access to the answer key, the agent's top-scoring
suspects are all real Enron convictions:

| Suspect | Score | Real POI? |
|---|---|---|
| Jeffrey Skilling | 0.99 | yes |
| Joseph Hirko | 0.99 | yes |
| Michael Kopper | 0.99 | yes (Fastow's lieutenant) |
| Kenneth Lay | 0.99 | yes |
| Vince Kaminski | 0.95 | no (false positive) |
| John Lavorato | 0.80 | no (false positive) |
| Mark Frevert | 0.70 | no (false positive) |

- **precision@3 = 100%**, precision@5 = 80%
- flagged-suspect precision (score >= 0.5) = 4/7 = 57%
- **recall = 4/18 = 22%**, average precision = 0.32

Notable: the agent surfaced Michael Kopper - a genuine POI who is nearly
invisible in the financial data - purely through the communication graph and
third-party email references, before it found Fastow himself.

## 3. Why CockroachDB (the sponsor's interest)

The system needs five capabilities simultaneously, which is the argument for a
single distributed SQL+vector store rather than a stack of separate systems:
- **Vector search** for semantic recall: ~956,000 email-chunk embeddings +
  20,325 per-person "writing-style" centroids in a distributed C-SPANN index.
- **ACID transactions** so a finding and its hashed evidence commit atomically
  and suspicion scores never go inconsistent.
- **Persistent agent state across crashes** - session state is in the DB, so
  kill/restart resumes exactly.
- **SQL joins across structured + semantic memory** - one query joins financial
  outliers, the graph, and vector-retrieved emails.
- **Distributed scale** - ~1M vectors, 363,355 graph edges today.

Evidence the vector memory carries real signal: querying Ken Lay's nearest
neighbours by writing-style centroid returns his actual secretary (Rosalee
Fleming) and chief of staff (Steven Kean) - the org chart reconstructed from
prose alone.

## 4. Architecture / data pipeline

- **Ingest (local):** 517,401 emails parsed from the CMU maildir into
  CockroachDB via bulk COPY, with resumable, self-healing person resolution
  across 87,505 inconsistent email addresses. Financial + POI data loaded; POI
  labels isolated in a `judge` schema.
- **Embeddings (local, GPU):** fastembed / all-MiniLM-L6-v2 (384-dim) on an
  RTX 2060 via onnxruntime-CUDA (fixed from a broken CPU path; ~50x speedup).
  956,398 chunks embedded and indexed with C-SPANN.
- **Graph:** 363,355 aggregated communication edges with PageRank and
  betweenness (NetworkX), stored back in CockroachDB.
- **Agent brain (local):** Qwen3-30B-A3B via Ollama on a separate machine
  ("johnson"), OpenAI-compatible tool-calling. No per-token cost. CockroachDB
  is the one always-on, consistent component - which is the point.
- **AWS:** Amazon S3 stores the 423MB corpus and a timestamped case-memory
  snapshot after every session; an S3 static website serves a read-only
  dashboard. CockroachDB Cloud itself runs on AWS (us-east-1).

## 5. The agent

12 investigative + memory tools: semantic_search, lookup_person, read_email,
financial_outliers (with a "quiet-money" flag for large payouts + low email
volume), graph_neighbors, bridge_nodes (betweenness), similar_people (centroid
distance), timeline, reputation (what OTHERS wrote about a person), plus
record_hypothesis, update_hypothesis, record_finding (evidence excerpts are
SHA-256 hashed on write for chain of custody), and update_suspect.

Session loop: resume memory from CockroachDB -> pick one lead -> work it with a
40-tool-call budget -> persist findings/scores -> write a session summary ->
back up to S3 -> exit. Prompt rules enforce scepticism: a "concealment gate"
(no score > 0.6 without deception evidence), a "corroboration rule" (verify via
third parties, not the suspect's own careful mail), and "breadth over depth"
(target new names, don't re-chase cleared ones).

## 6. Requirements compliance

- **CockroachDB tools used (need >= 2, used 3):** Distributed Vector Indexing
  (C-SPANN); Managed MCP Server (read-only, audit-logged, wired via `.mcp.json`
  and authenticated); Agent Skills / operational workflows incl. session-end
  backups.
- **AWS services used (need >= 1, used 2):** Amazon S3 (corpus + snapshots) and
  S3 static-site hosting.
- **Deliverables:** public MIT repo; live dashboards (Cloudflare tunnel + AWS
  static site); a zero-setup offline demo (`demo/index.html`, real recorded
  snapshots, no backend); a turnkey 3-min video script. Video not yet recorded.

## 7. Dashboards / visualisation

Live at coldcase.savagealgo.com (Inter typography, SVG icon set, no emoji):
- Suspect board with tiered-colour scores and rationales.
- A force-directed communication graph: glowing labelled suspect nodes,
  influence-sized employee nodes, hover-to-trace a person's contacts, drag.
- A **memory-replay** page: scrub a slider through the timestamped S3 snapshots
  to watch suspects appear and scores climb; clickable tabs reveal the actual
  hypotheses (with status badges), findings, and verbatim evidence excerpts at
  each point in time.
- An AWS-hosted static board reading the public snapshot.

## 8. Experiments (documented honestly in docs/EXPERIMENTS.md)

- **E1 breadth prompting - WORKED:** lifted recall 3->4/18 and surfaced Kopper
  via the graph.
- **E2 quiet-money financial signal - PARTIAL:** highlights low-email/high-payout
  actors; corrected our wrong assumption that Fastow's $81M loan was his (it is
  Lay's - Fastow is financially invisible here).
- **E3 stance self-critique - FAILED (instructive):** classifying a suspect's
  stance from their OWN mail demoted the real culprits too, because perpetrators
  and whistleblowers both look innocent in their own writing. Reverted; kept as
  a documented negative result.
- **E4 third-party reputation review - PARTIAL:** judging by what OTHERS write
  correctly caught both false positives (Kaminski, Lavorato) AND both clear
  principals (Skilling, Kopper), but over-demoted two real POIs (Lay, Hirko)
  whose accusatory evidence is not in this corpus. Net-negative if applied, so
  kept dry-run only.
- **E5 recall plateau - documented:** by ~45 sessions the agent autonomously
  investigates the correct remaining POIs (Koenig, Rieker - both real
  convictions) but declines to flag them without sufficient evidence. Recall is
  bounded by corpus coverage and a deliberately high evidence bar, not by the
  memory architecture.

## 9. Known limitations (stated plainly)

- **Recall is 4/18.** Many labelled POIs (Fastow, Koenig, Rieker) have little
  incriminating content in the email corpus; their culpability is in filings and
  testimony. The agent conservatively declines to guess.
- **Two-to-three false positives** (Kaminski, Lavorato, Frevert). Kaminski is
  the classic whistleblower trap (Enron's risk officer who warned against the
  deals). Distinguishing "discusses fraud" from "commits fraud" is unsolved with
  a local model.
- **Throughput** is bounded by a shared local GPU (the agent LLM), not by
  CockroachDB, which stays fast throughout. Session batches are slow when the
  GPU is busy with other work.
- **The demo video is not yet recorded**, and credentials shared during
  development need rotation before submission.

## 10. Judging-criteria self-assessment (be critical of this)

- *Agentic Memory Design:* strong - memory is the product; kill/resume works;
  ~1M vectors + transactional case tables + score-history log.
- *Technical Implementation:* strong - real C-SPANN queries, bulk ingest, 12
  tools, hashed evidence, an ablation, and 5 documented experiments.
- *Real-World Impact:* strong framing (e-discovery / fraud) with a quantified,
  ground-truth benchmark - but recall 22% is the soft spot.
- *Production Readiness:* strong - RBAC-sealed ground truth (provable blind),
  read-only audit-logged MCP, S3 evidence backups, least-privilege agent role.
- *Creativity:* strong - solving a real historical case blind, scored against
  convictions, with an honest experiment log.

## 11. The single strongest piece of evidence

An **ablation**: the same agent run with vs without persistent memory.
Without memory, three independent sessions each fixate on the same wrong first
lead and find **0/18 POIs at 0% precision@3**. With CockroachDB memory it
accumulates to **4/18 at 100% precision@3**. Persistent memory is the
difference between finding the perpetrators and finding nothing.

---

## Questions we would like a reviewer to weigh in on

1. Is recall 4/18 a fatal weakness for the "Real-World Impact" score, or is the
   conservative-precision framing (E5) a defensible, even positive, story?
2. Is the local-LLM / local-embeddings choice (with only CockroachDB as the
   always-on component) a strength (reproducible, cost-free, honest) or a
   weakness (judges may want Amazon Bedrock used)?
3. Which single addition would most raise the score: recording the video,
   a multi-signal scoring model to lift recall, joining a second data source
   (filings) to the memory, or something else?
4. Does the honest experiment log (including two failures) help or hurt with
   hackathon judges?
