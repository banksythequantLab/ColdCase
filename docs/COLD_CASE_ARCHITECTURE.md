# Cold Case — Autonomous Financial-Crimes Investigator

**CockroachDB × AWS Hackathon — Build with Agentic Memory** (deadline Aug 18, 2026, 5:00pm EDT)

An AI agent that investigates the Enron fraud blind — using CockroachDB as its persistent
case memory — and independently rediscovers the real Persons of Interest, with evidence trails.

---

## 1. Concept

The Enron corpus (~500K real emails, ~150 employees) plus the financial dataset
(146 employees, 14 financial features, **18 labeled Persons of Interest**) gives us
ground truth. The agent never sees the POI labels. It investigates over multiple
sessions, persisting every hypothesis, finding, and evidence chain in CockroachDB.
The demo compares its suspect list against the real convictions.

**Pitch line:** "We gave an agent 500,000 emails and a database that never forgets.
It solved Enron."

### Judging criteria mapping

| Criterion | How we hit it |
|---|---|
| Agentic Memory Design | Case memory (hypotheses, findings, evidence), 500K+ embedding rows, entity graph, session state — all transactional, all queried constantly |
| Technical Implementation | C-SPANN vector index, managed MCP (read-only + audit), Agent Skills for schema/ops, correct pgvector API usage |
| Real-World Impact | Fraud detection / e-discovery / compliance — a real industry; validated against ground truth |
| Production Readiness | Read-only MCP, service-account RBAC, audit logging, evidence-row hashing (chain of custody), resilience demo |
| Creativity | Agent solves a historical fraud case blind, with quantifiable results |

---

## 2. Data sources

| Dataset | Source | Size |
|---|---|---|
| Enron email corpus | CMU (`enron_mail_20150507.tar.gz`) or Kaggle CSV | 422MB gz / 1.4GB raw, ~500K emails |
| POI financial dataset | Udacity ud120 `final_project_dataset.pkl` (mirrors on GitHub) | 146 people × 21 features, 18 POI labels |

POI labels are loaded into a **judge-only** table the agent has no grant on —
used solely for scoring at demo time.

---

## 3. CockroachDB schema

```sql
-- People (from corpus headers + financial dataset)
CREATE TABLE persons (
  person_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name    STRING NOT NULL,
  title        STRING,
  emails       STRING[] NOT NULL,          -- known addresses
  UNIQUE INDEX (full_name)
);

-- Financial features (agent-visible; NO poi label here)
CREATE TABLE financial_profiles (
  person_id UUID PRIMARY KEY REFERENCES persons,
  salary INT8, bonus INT8, total_payments INT8, loan_advances INT8,
  deferred_income INT8, exercised_stock_options INT8, restricted_stock INT8,
  total_stock_value INT8, long_term_incentive INT8, expenses INT8,
  director_fees INT8, other INT8
);

-- Ground truth, separate DB role, agent has zero grants
CREATE TABLE judge.poi_labels (
  person_id UUID PRIMARY KEY,
  is_poi BOOL NOT NULL
);

-- Emails
CREATE TABLE emails (
  email_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id   STRING UNIQUE,
  sender_id    UUID REFERENCES persons,
  sent_at      TIMESTAMPTZ,
  subject      STRING,
  body         STRING,
  folder       STRING,
  body_sha256  BYTES NOT NULL,             -- chain of custody
  INDEX (sender_id, sent_at)
);

CREATE TABLE email_recipients (
  email_id  UUID REFERENCES emails,
  person_id UUID REFERENCES persons,
  kind      STRING CHECK (kind IN ('to','cc','bcc')),
  PRIMARY KEY (email_id, person_id, kind)
);

-- Embeddings: chunked bodies, Titan V2 = 1024 dims
CREATE TABLE email_chunks (
  chunk_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id  UUID REFERENCES emails,
  seq       INT2,
  text      STRING,
  embedding VECTOR(1024),
  VECTOR INDEX (embedding)                 -- C-SPANN distributed index
);

-- Behavioral profile per person (aggregate embedding + graph stats)
CREATE TABLE person_profiles (
  person_id        UUID PRIMARY KEY REFERENCES persons,
  centroid         VECTOR(1024),           -- mean of sent-mail embeddings
  sent_count INT8, recv_count INT8,
  betweenness FLOAT8, pagerank FLOAT8,     -- computed offline, stored
  after_hours_ratio FLOAT8,
  VECTOR INDEX (centroid)
);

-- Communication graph edges (aggregated)
CREATE TABLE comm_edges (
  src UUID REFERENCES persons,
  dst UUID REFERENCES persons,
  msg_count INT8, first_at TIMESTAMPTZ, last_at TIMESTAMPTZ,
  PRIMARY KEY (src, dst)
);

-- ===== Agent case memory =====
CREATE TABLE investigations (
  case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title STRING, status STRING, created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE hypotheses (
  hypothesis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES investigations,
  statement STRING,
  confidence FLOAT8,                       -- agent-updated over sessions
  status STRING CHECK (status IN ('open','supported','refuted')),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE findings (
  finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hypothesis_id UUID REFERENCES hypotheses,
  summary STRING,
  method STRING,                           -- 'vector_search'|'graph'|'financial_outlier'|...
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE evidence (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID REFERENCES findings,
  email_id UUID REFERENCES emails,
  excerpt STRING,
  excerpt_sha256 BYTES                     -- tamper-evident
);

CREATE TABLE suspects (
  case_id UUID REFERENCES investigations,
  person_id UUID REFERENCES persons,
  suspicion_score FLOAT8,
  rationale STRING,
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (case_id, person_id)
);

CREATE TABLE agent_sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES investigations,
  started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ,
  summary STRING                           -- what the agent did; read at next session start
);
```

Session resume = `SELECT` open hypotheses + last session summaries + top suspects.
Suspect-score updates and evidence inserts run in serializable transactions.

---

## 4. Agent design

**Runtime:** Python (LangChain or plain SDK) on ECS Fargate; Bedrock for cognition.

**Models:** Claude Haiku-class on Bedrock for routine tool loops; escalate to a
larger model for session-end synthesis and final report. Titan Text Embeddings V2
(1024-dim) for all embeddings.

**Investigative tools (agent-callable):**

1. `semantic_search(query, k)` — vector search over `email_chunks`
2. `similar_people(person_id, k)` — vector search over `person_profiles.centroid`
3. `financial_outliers()` — SQL z-scores over `financial_profiles`
4. `graph_neighbors(person_id)` / `bridge_nodes()` — `comm_edges` + stored centrality
5. `timeline(person_id | topic)` — email volume around key dates
6. `read_email(email_id)` — full body
7. Memory writes: `record_hypothesis`, `record_finding`, `attach_evidence`, `update_suspect`

**Loop (per session, ~30–60 tool calls):**
resume memory → pick highest-value open hypothesis → run 1–3 investigative moves →
write findings + evidence → adjust suspicion scores → write session summary → exit.
Multiple sessions = the persistence story.

---

## 5. Hackathon tool usage (requirement: ≥2 CRDB tools, ≥1 AWS)

| Tool | Role |
|---|---|
| **CRDB Distributed Vector Indexing** ✅ | C-SPANN indexes on 500K+ chunks and person centroids; core of semantic recall |
| **CRDB Managed MCP Server** ✅ | (a) used during development from Claude Code; (b) demo: judges interrogate the case live ("who's the top suspect and why?") — read-only, audit-logged |
| **CRDB Agent Skills Repo** ✅ | schema design, query tuning, observability skills used during build; documented in README |
| **ccloud CLI** (stretch) | agent-driven backup of case DB at session end ("the agent preserves its own evidence") |
| **Amazon Bedrock** ✅ | Haiku + Titan embeddings |
| **Amazon S3** ✅ | raw corpus + generated case reports |
| **Amazon ECS (Fargate)** ✅ | agent runtime + ingestion jobs |
| **AWS Lambda** (optional) | session scheduler (EventBridge → Lambda → ECS task) |

---

## 6. Ingestion pipeline

1. S3 upload of raw corpus (one-time)
2. ECS batch job: parse maildir → dedupe by Message-ID → resolve persons/aliases → insert emails + recipients (batched, ~500 rows/txn)
3. Chunk (~512 tokens) → Titan V2 embed (batch) → insert `email_chunks`
4. Offline compute: comm_edges aggregation, centrality (NetworkX), person centroids
5. Load financial dataset; POI labels into `judge` schema only

**Cost:** embeddings ≲ $35 total; CRDB within $400 free credits (~5GB storage);
Bedrock agent runs a few dollars per full investigation.

---

## 7. Production readiness story

- Agent connects via service account with grants only on agent-visible tables; zero access to `judge` schema
- MCP endpoint read-only with full audit logging — every judge query is logged
- Evidence rows carry SHA-256 of excerpts → tamper-evident chain of custody
- Resilience demo: kill the agent mid-session, restart → resumes exactly; CRDB survives node loss with zero lost writes
- Observability: session table + CRDB console metrics

---

## 8. Demo video arc (<3 min)

1. (0:00) The case: 500K real emails, agent knows nothing about who was guilty
2. (0:30) Ingestion at scale — row counts, vector index live
3. (0:50) Agent investigates: watch hypotheses/findings/evidence rows appear
4. (1:30) Kill the agent process → restart → picks up mid-investigation (memory story)
5. (1:50) Reveal: suspect list vs. real POI labels — precision/recall on screen
6. (2:20) Judges' view: query the case through the managed MCP server in plain English
7. (2:50) Architecture slide + close

---

## 9. Submission checklist (Devpost requirements)

- [ ] Public repo, MIT/Apache-2.0 license visible in About section
- [ ] README: setup, run instructions, dependencies, example config
- [ ] Functional demo app URL (suspect-board web UI, see build plan)
- [ ] YouTube/Vimeo video < 3 min, public
- [ ] Written: which CRDB tools used and how (§5)
- [ ] Written: which AWS services used and how (§5)
- [ ] Optional: architecture diagram, CRDB tool feedback
