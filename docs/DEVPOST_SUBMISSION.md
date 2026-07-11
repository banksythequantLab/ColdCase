# Cold Case — Devpost Submission Draft

**Tagline:** An autonomous financial-crimes investigator that never forgets. We
gave an AI agent 500,000 real Enron emails, hid the list of who was convicted,
and let it solve the case from scratch — with CockroachDB as its memory.

---

## Inspiration

The Enron email corpus exists because of a fraud investigation. 500,000 real
emails from ~150 executives, released during the prosecution that put people in
prison. It felt like the perfect adversary for an agent whose entire value
proposition is memory: a real case, with a real answer key (18 documented
"Persons of Interest"), that no single human could hold in their head.

An investigator's power *is* their memory — every thread pulled, every
contradiction spotted across thousands of documents, every hunch that pays off
weeks later. That is exactly what agents lack and exactly what CockroachDB
provides. So we built an agent that investigates Enron the way a cold-case
detective would: over many sessions, forgetting nothing, building an
evidence-backed suspect list — and we score it against the real convictions.

## What it does

Cold Case runs autonomous investigation sessions against the Enron corpus. In
each session the agent:

1. **Resumes its memory** from CockroachDB — open hypotheses, prior findings,
   the current suspect board, and summaries of past sessions.
2. **Pursues one line of inquiry** using investigative tools: semantic search
   over 956,398 email embeddings, financial-outlier detection, communication-
   graph analysis (betweenness, neighbors), behavioral similarity (vector
   distance between people's writing profiles), and full email reads.
3. **Persists everything it learns** — hypotheses, findings with verbatim
   evidence excerpts (each SHA-256 hashed for chain of custody), and updated
   suspicion scores with rationales.
4. **Writes a session summary** and exits. Kill the process mid-session and it
   loses nothing; the next session picks up exactly where it left off.

Crucially, **the agent never sees the answer key.** The 18 real POI labels live
in a separate CockroachDB schema (`judge`) that the agent's database role has
zero privileges on — enforced by RBAC, not by trust. Only an admin scoring
script can read them.

### Results (blind)

After a run of sessions on a fresh case, the agent's top suspects were **Jeffrey
Skilling (0.99)** and **Kenneth Lay (0.99)** — the two most famous Enron
convictions — each supported by real evidence it found itself: Lay's $80M
change-of-control severance provision, Skilling's role structuring off-book
entities. Its highest-conviction picks are real POIs; it correctly *cleared*
high-earning executives when the emails showed no evidence of concealment.

It also revealed a genuinely instructive failure mode: it flagged Vince Kaminski
(Enron's head of risk) because his mail is saturated with SPV discussion — when
in fact he was the internal voice *warning against* those deals. That is the
classic investigator's trap (mistaking the whistleblower for the culprit), and
we used it to iterate the agent's reasoning rules. This honesty about what the
memory-driven agent gets right and wrong is, we think, part of the story.

## How we built it

**Memory layer — CockroachDB Cloud (Standard, on AWS us-east-1):**
- **Distributed Vector Indexing (C-SPANN):** 956,398 email-body chunk
  embeddings + 20,325 per-person "writing profile" centroids, all indexed for
  semantic recall. The vector space alone reconstructed Enron's org chart —
  Ken Lay's nearest neighbors by writing style are his actual secretary and
  chief of staff.
- **Transactional case memory:** hypotheses, findings, evidence (hashed),
  suspects, and session state — the tables the agent reads and writes every
  session. Serializable transactions keep evidence and scores consistent.
- **Communication graph:** 363,355 aggregated edges with pagerank and
  betweenness for finding hidden intermediaries.

**Managed MCP Server:** wired into Claude Code via a project `.mcp.json`, giving
natural-language, read-only, audit-logged access to the live case ("who is the
top suspect and why?"). Safe by default — the endpoint requires auth and logs
every query.

**Agent Skills / ccloud CLI:** used during build for schema design and cluster
operations.

**AWS:** Amazon S3 stores the raw 423MB corpus and the exported case reports.

**Local-first cognition:** to keep the whole pipeline reproducible and free of
per-token cost, embeddings run on-prem (fastembed / all-MiniLM-L6-v2, 384-dim)
and the agent brain is a local Qwen3-30B via Ollama. CockroachDB is the one
piece that has to be always-on and consistent — which is exactly the point.

**Live dashboard:** a FastAPI app (coldcase.savagealgo.com via Cloudflare
tunnel) shows ingestion, the suspect board, and case-memory stats in real time.

## Which CockroachDB tools we used and how

- **Distributed Vector Indexing** — the agent's semantic memory: every
  investigative "recall" is a C-SPANN vector search over ~1M embeddings; person
  similarity is vector distance between writing-style centroids.
- **Managed MCP Server** — human/agent inspection of the live case in natural
  language, read-only and audit-logged.
- **Agent Skills Repo** — schema and operational workflows during build.

## Which AWS services we used and how

- **Amazon S3** — durable storage of the source corpus (artifact) and the
  agent's exported case reports (documents).

## Challenges

Bulk-loading 500K emails efficiently (switched from row inserts to `COPY`),
resolving 87,505 people across inconsistent address formats, and the honest
tuning problem of teaching a local model to distinguish *discussing* fraud from
*committing* it. Windows/CUDA quirks pushed embeddings to CPU — still finished
the full corpus overnight.

## What's next

Stance-aware scoring to beat the whistleblower trap; a "quiet-money" heuristic
to surface actors like Fastow who avoided email but left financial fingerprints;
and deploying the agent runtime on AWS Lambda/ECS for the hosted demo.

## Try it

- Code: https://github.com/banksythequantLab/ColdCase (MIT)
- Live dashboard: https://coldcase.savagealgo.com
