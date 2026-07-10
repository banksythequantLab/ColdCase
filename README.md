# Cold Case 🕵️

**An autonomous financial-crimes investigator with persistent memory, built on
CockroachDB + AWS Bedrock.**

Submission for the [CockroachDB × AWS Hackathon — Build with Agentic Memory](https://cockroachdb-ai.devpost.com/).

We gave an AI agent the real Enron email corpus (~500K emails) and financial
records — with the Person-of-Interest labels hidden — and a database that never
forgets. It investigates over multiple sessions, persisting every hypothesis,
finding, and evidence chain in CockroachDB, then we score its suspect list
against the real convictions.

## Architecture

- **CockroachDB Cloud** — persistent case memory: 500K+ email embeddings
  (C-SPANN distributed vector index), entity/communication graph, transactional
  hypothesis/finding/evidence/suspect tables
- **CockroachDB Managed MCP Server** — read-only, audit-logged natural-language
  access to the live case (used in dev and by judges)
- **Amazon Bedrock** — Claude (agent cognition) + Titan Text Embeddings V2
- **Amazon S3** — raw corpus + case reports; **ECS Fargate** — agent runtime

## CockroachDB tools used

1. Distributed Vector Indexing — semantic recall over email chunks + behavioral
   person profiles
2. Managed MCP Server — live case interrogation, read-only + audit logging
3. Agent Skills Repo — schema design, query tuning, ops workflows during build

## Quick start

```
pip install -r requirements.txt
cp .env.example .env       # fill in CRDB + AWS credentials
psql "$CRDB_ADMIN_URL" -f sql/schema.sql
python src/ingest/parse_maildir.py data/maildir
python src/ingest/embed_chunks.py
python src/agent/investigator.py --new-case "Enron"
```

See `docs/COLD_CASE_ARCHITECTURE.md` and `docs/COLD_CASE_BUILD_PLAN.md`.

## Ground-truth isolation

POI labels live in a `judge` schema the agent's service account has **zero
grants** on. The "solved it blind" claim is enforced by RBAC, not by promise.

## License

MIT
