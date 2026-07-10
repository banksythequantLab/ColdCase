-- Cold Case: CockroachDB schema
-- Apply with admin connection: psql "$CRDB_ADMIN_URL" -f sql/schema.sql

CREATE DATABASE IF NOT EXISTS coldcase;
SET DATABASE = coldcase;

CREATE TABLE IF NOT EXISTS persons (
  person_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name    STRING NOT NULL,
  title        STRING,
  emails       STRING[] NOT NULL,
  UNIQUE INDEX persons_name_idx (full_name)
);

-- Agent-visible financial features. NO poi label here.
CREATE TABLE IF NOT EXISTS financial_profiles (
  person_id UUID PRIMARY KEY REFERENCES persons,
  salary INT8, bonus INT8, total_payments INT8, loan_advances INT8,
  deferred_income INT8, exercised_stock_options INT8, restricted_stock INT8,
  total_stock_value INT8, long_term_incentive INT8, expenses INT8,
  director_fees INT8, other INT8
);

-- Ground truth: separate schema, agent role gets ZERO grants here.
CREATE SCHEMA IF NOT EXISTS judge;
CREATE TABLE IF NOT EXISTS judge.poi_labels (
  person_id UUID PRIMARY KEY,
  is_poi BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS emails (
  email_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id   STRING UNIQUE,
  sender_id    UUID REFERENCES persons,
  sent_at      TIMESTAMPTZ,
  subject      STRING,
  body         STRING,
  folder       STRING,
  body_sha256  BYTES NOT NULL,
  INDEX emails_sender_time_idx (sender_id, sent_at)
);

CREATE TABLE IF NOT EXISTS email_recipients (
  email_id  UUID REFERENCES emails,
  person_id UUID REFERENCES persons,
  kind      STRING CHECK (kind IN ('to','cc','bcc')),
  PRIMARY KEY (email_id, person_id, kind)
);

-- Embeddings: Titan Text Embeddings V2, 1024 dims. C-SPANN vector index.
CREATE TABLE IF NOT EXISTS email_chunks (
  chunk_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id  UUID REFERENCES emails,
  seq       INT2,
  text      STRING,
  embedding VECTOR(1024),
  VECTOR INDEX email_chunks_embedding_idx (embedding)
);

CREATE TABLE IF NOT EXISTS person_profiles (
  person_id         UUID PRIMARY KEY REFERENCES persons,
  centroid          VECTOR(1024),
  sent_count INT8, recv_count INT8,
  betweenness FLOAT8, pagerank FLOAT8,
  after_hours_ratio FLOAT8,
  VECTOR INDEX person_profiles_centroid_idx (centroid)
);

CREATE TABLE IF NOT EXISTS comm_edges (
  src UUID REFERENCES persons,
  dst UUID REFERENCES persons,
  msg_count INT8,
  first_at TIMESTAMPTZ,
  last_at TIMESTAMPTZ,
  PRIMARY KEY (src, dst)
);

-- ===== Agent case memory =====
CREATE TABLE IF NOT EXISTS investigations (
  case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title STRING,
  status STRING DEFAULT 'open',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hypotheses (
  hypothesis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES investigations,
  statement STRING,
  confidence FLOAT8 DEFAULT 0.5,
  status STRING DEFAULT 'open' CHECK (status IN ('open','supported','refuted')),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS findings (
  finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hypothesis_id UUID REFERENCES hypotheses,
  summary STRING,
  method STRING,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID REFERENCES findings,
  email_id UUID REFERENCES emails,
  excerpt STRING,
  excerpt_sha256 BYTES
);

CREATE TABLE IF NOT EXISTS suspects (
  case_id UUID REFERENCES investigations,
  person_id UUID REFERENCES persons,
  suspicion_score FLOAT8,
  rationale STRING,
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (case_id, person_id)
);

CREATE TABLE IF NOT EXISTS agent_sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES investigations,
  started_at TIMESTAMPTZ DEFAULT now(),
  ended_at TIMESTAMPTZ,
  summary STRING
);
