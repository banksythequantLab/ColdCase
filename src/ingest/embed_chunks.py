"""Chunk email bodies and embed with Titan Text Embeddings V2 (1024-dim).

Usage: python src/ingest/embed_chunks.py
Status: SKELETON — untested. Week 2 deliverable.
Bedrock invoke_model request shape for Titan V2 to be verified against
current AWS docs at implementation time (Context7/AWS docs).
"""
import json
import os

import boto3
import psycopg
from dotenv import load_dotenv

load_dotenv()
CHUNK_TOKENS = 512  # approx; split on paragraphs then merge


def embed(client, text):
    resp = client.invoke_model(
        modelId=os.environ["BEDROCK_EMBED_MODEL"],
        body=json.dumps({"inputText": text, "dimensions": 1024}),
    )
    return json.loads(resp["body"].read())["embedding"]


def main():
    bedrock = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
    conn = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
    # TODO Week 2:
    #  SELECT email_id, body FROM emails WHERE email_id NOT IN
    #    (SELECT DISTINCT email_id FROM email_chunks)  -- resumable
    #  chunk -> embed -> INSERT INTO email_chunks (batched)
    raise NotImplementedError


if __name__ == "__main__":
    main()
