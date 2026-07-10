-- RBAC: the agent can never see ground truth.
-- Run as admin AFTER creating the coldcase_agent SQL user in CockroachDB Cloud.

GRANT SELECT ON TABLE coldcase.public.persons,
  coldcase.public.financial_profiles, coldcase.public.emails,
  coldcase.public.email_recipients, coldcase.public.email_chunks,
  coldcase.public.person_profiles, coldcase.public.comm_edges
  TO coldcase_agent;

GRANT SELECT, INSERT, UPDATE ON TABLE coldcase.public.investigations,
  coldcase.public.hypotheses, coldcase.public.findings,
  coldcase.public.evidence, coldcase.public.suspects,
  coldcase.public.agent_sessions
  TO coldcase_agent;

-- NO grants on schema judge. Verify:
--   SHOW GRANTS ON judge.poi_labels;  -- coldcase_agent must not appear
