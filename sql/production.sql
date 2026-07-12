-- Production extras: health monitoring + reasoning-graph schema.
-- Apply: psql "$CRDB_ADMIN_URL" -f sql/production.sql

-- 1) Health-check view: freshness + volume at a glance.
CREATE OR REPLACE VIEW system_health AS
SELECT
  (SELECT count(*) FROM emails)                         AS emails,
  (SELECT count(*) FROM email_chunks)                   AS embeddings,
  (SELECT count(*) FROM comm_edges)                     AS graph_edges,
  (SELECT count(*) FROM person_profiles
     WHERE centroid IS NOT NULL)                        AS person_centroids,
  (SELECT count(*) FROM agent_sessions)                 AS sessions_run,
  (SELECT max(ended_at) FROM agent_sessions)            AS last_session_at,
  (SELECT now() - max(ended_at) FROM agent_sessions)    AS session_staleness,
  (SELECT count(*) FROM evidence)                       AS evidence_rows;

-- 2) Reasoning graph: how one finding connects to another (temporal
--    reasoning + explainability). Lets you ask "why was X flagged?" and
--    detect circular reasoning or evidence built on discredited premises.
CREATE TABLE IF NOT EXISTS reasoning_edges (
  edge_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         UUID REFERENCES investigations,
  from_finding_id UUID REFERENCES findings,
  to_finding_id   UUID REFERENCES findings,
  relationship    STRING CHECK (relationship IN
                    ('corroborates','contradicts','implies','supersedes')),
  confidence_impact FLOAT8,
  discovered_at   TIMESTAMPTZ DEFAULT now(),
  INDEX (from_finding_id),
  INDEX (to_finding_id)
);
GRANT SELECT, INSERT ON TABLE coldcase.public.reasoning_edges TO coldcase_agent;
