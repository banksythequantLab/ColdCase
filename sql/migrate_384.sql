-- Switch to 384-dim local embeddings (all-MiniLM-L6-v2, apples-to-apples
-- with prior enron-loader system). email_chunks is empty; centroid all NULL.
DROP TABLE IF EXISTS email_chunks;
CREATE TABLE email_chunks (
  chunk_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id  UUID REFERENCES emails,
  seq       INT2,
  text      STRING,
  embedding VECTOR(384),
  VECTOR INDEX email_chunks_embedding_idx (embedding)
);
GRANT SELECT ON TABLE coldcase.public.email_chunks TO coldcase_agent;

ALTER TABLE person_profiles DROP COLUMN IF EXISTS centroid;
ALTER TABLE person_profiles ADD COLUMN centroid VECTOR(384);
CREATE VECTOR INDEX IF NOT EXISTS person_profiles_centroid_idx
  ON person_profiles (centroid);
