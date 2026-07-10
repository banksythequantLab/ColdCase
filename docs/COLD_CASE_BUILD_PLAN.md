# Cold Case — Build Plan (Jul 10 → Aug 18, 2026)

5.5 weeks to the Devpost deadline (Aug 18, 5:00pm EDT). Rule: **working end-to-end
slice by end of Week 2**, polish and scale after. Video + submission get a full week.

---

## Week 1 (Jul 10–19) — Foundations & data

- Register on Devpost; create CockroachDB Cloud org ($400 credits) + AWS account/budget alarm
- Create public GitHub repo, MIT license, skeleton README (license visible day 1)
- Download CMU corpus → S3; download POI financial dataset
- Stand up CRDB Standard cluster (AWS region); apply schema
- Enable managed MCP server; connect from Claude Code — verify it works early
- Ingestion v1: parse maildir → persons, emails, email_recipients (dedupe, alias resolution)
- **Milestone:** 500K emails queryable in CRDB; MCP answers "how many emails did Ken Lay send?"

## Week 2 (Jul 20–26) — Embeddings, graph, first agent loop

- Chunk + embed via Titan V2 (batch job on ECS); load `email_chunks`; build C-SPANN index
- Compute comm_edges, centrality, person centroids; load financial_profiles; POI labels → judge schema
- Agent v1: Bedrock Haiku + 3 tools (semantic_search, financial_outliers, record_finding)
- Case-memory tables wired; agent completes one 20-tool-call session and resumes after restart
- **Milestone:** end-to-end thin slice — agent investigates, memory persists, vector search works

## Week 3 (Jul 27–Aug 2) — Full investigator

- All 7 investigative tools + all memory-write tools
- Session loop: resume → hypothesis selection → investigate → score suspects → summarize
- Model escalation (Haiku loop / bigger model for synthesis)
- Run 5–10 full multi-session investigations; tune prompts until suspect list is credible
- First scoring run against held-out POI labels (precision/recall@10)
- **Milestone:** agent independently flags majority of real POIs with evidence trails

## Week 4 (Aug 3–9) — Demo app & production story

- Suspect-board web UI (the "functional demo app" requirement): live suspects table,
  hypothesis feed, evidence viewer, network graph visualization — reads CRDB directly
- Deploy UI (Fargate or Lambda+CloudFront); public URL
- RBAC: agent service account, judge schema isolation; evidence hashing verified
- Resilience test on camera: kill agent mid-session, kill scenario for DB story
- Use Agent Skills repo for index/query tuning; log usage for README
- Stretch: ccloud CLI agent-triggered backup at session end
- **Milestone:** public demo URL live; all judging-criteria claims actually true

## Week 5 (Aug 10–14) — Video & submission

- Script + record 3-min video (arc in architecture doc §8); upload to YouTube
- README polish: setup/run instructions, architecture diagram, CRDB + AWS tool writeups
- Fresh-clone test: follow README on a clean machine, fix gaps
- Draft Devpost submission text; optional CRDB tools feedback section
- **Milestone:** submission 100% draft-complete by Aug 14

## Buffer (Aug 15–18) — Submit early

- Final fixes only; submit by **Aug 17** (never the deadline hour)

---

## Scope guards (cut in this order if behind)

1. ccloud CLI backup integration (stretch — drop first)
2. Network graph viz in UI (static image fallback)
3. Full 500K corpus → subset to ~150K core-custodian emails (still "real scale")
4. Lambda scheduler → run sessions manually

## Do-not-cut list

- MCP live-query demo (judge magnet)
- Kill/resume persistence demo
- Ground-truth scoring reveal
- Public demo URL + license + video (hard requirements)

## Budget estimate

| Item | Est. |
|---|---|
| Embeddings (Titan V2, ~150M tokens) | ≤ $35 |
| Bedrock agent runs (dev + final) | $20–60 |
| CRDB (within $400 credits) | $0 |
| AWS compute (Fargate, S3) | $20–50 |
| **Total out of pocket** | **≈ $75–150, likely less** |
