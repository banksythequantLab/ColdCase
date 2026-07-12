# Brief for the reviewers: what should the 3rd E-Discovery entry be?

*Paste this to your AI reviewers to source and stress-test a third submission.*

## Context

We're entering the **CockroachDB × AWS "Build with Agentic Memory" hackathon**
(deadline Aug 18, 2026). Rules allow multiple submissions per entrant **if each
is unique and substantially different**; a project can win at most one prize, so
extra entries are extra independent shots at the top 3 (only ~112 participants,
3 prizes). Everything must be newly built in the submission window, use **≥2
CockroachDB tools** (we use Distributed Vector Indexing / C-SPANN, the Managed
MCP Server, and Agent Skills / ops) and **≥1 AWS service** (we use S3 + S3
static hosting; Bedrock/SageMaker optional).

We are building a suite under the **Nota.Lawyer** brand: agentic e-discovery
tools that all share one CockroachDB memory backbone (vectors + graph +
transactional case state) and a local-LLM + local-embeddings stack (so wins are
attributable to *memory*, not model).

## Entry #1 — Cold Case (built, strong)

Autonomous financial-crimes **investigator**. Given 517,401 real Enron emails +
22 SEC filings with the conviction list hidden in an RBAC-sealed schema, it
finds bad actors *blind*: top-3 suspects are all real convictions (100%
precision@3), proven decisive by an ablation (0/18 without memory → 4/18 with).
Persists hypotheses/findings/evidence/scores across sessions; resumes after
crashes. Honest experiment log incl. documented failures.

## Entry #2 — Ledger (candidate: SEC financial-forensics)

Ingests SEC filings (10-K/10-Q/8-K/proxy) and flags **accounting anomalies and
restatement signals** — related-party structures, off-balance-sheet vehicles,
period-over-period discrepancies — with memory of prior findings. Distinct from
Cold Case: filings not email, anomaly detection not person-attribution. The
filings pipeline already exists.

## What we're asking you

Propose the **strongest possible 3rd entry** that is *substantially different*
from #1 and #2, maximizes the five equally-weighted judging criteria (Agentic
Memory Design, Technical Implementation, Real-World Impact, Product Readiness,
Creativity & Originality), and genuinely needs CockroachDB's *persistent,
transactional, multi-modal memory* (not just a vector store). For each idea give:

1. One-line pitch and the distinct e-discovery job it does.
2. Why persistent CockroachDB memory is essential (what breaks without it).
3. A concrete, buildable demo with an objective success measure (ideally a
   public dataset with ground truth, like Enron).
4. The single biggest risk.

Candidates we're weighing (critique or beat them):
- **Privilege** — attorney-client privilege review: flags privileged docs and
  inadvertent disclosures, remembering prior privilege determinations + rationale.
- **Chronicle** — case timeline/chronology reconstruction from a corpus, resolving
  actors, dates, and events with cross-session memory.
- **Redaction Sentinel** — PII/PHI detection + redaction with a tamper-evident
  audit trail and memory of redaction rules.
- **Production/Responsiveness** — classifies which docs are responsive to a
  discovery request, keeping determinations consistent across a rolling review.

Rank them, or propose something better. Be blunt about which would actually
place in a technical hackathon vs. which just sounds good.
