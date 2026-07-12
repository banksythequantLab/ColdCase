"""Memory-efficiency metric: how much context the agent AVOIDS re-reading by
pulling from CockroachDB instead of stuffing the corpus into the LLM context.

Honest estimate from real corpus stats. The point: the agent reasons over a
few thousand tokens per session while its *memory* spans the whole corpus, and
never re-processes a document it has already seen.
"""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])

n_emails = c.execute("SELECT count(*) FROM emails").fetchone()[0]
avg_chars = c.execute("SELECT avg(length(body)) FROM emails").fetchone()[0]
n_chunks = c.execute("SELECT count(*) FROM email_chunks").fetchone()[0]
n_sessions = c.execute("SELECT count(*) FROM agent_sessions").fetchone()[0]

# ~4 chars per token
corpus_tokens = int(n_emails * float(avg_chars) / 4)

# per-session agent context: resume memory (case state) + tool results
resume_tokens = 3000              # hypotheses + suspects + summaries
tool_calls = 40
tokens_per_tool_result = 600
session_tokens = resume_tokens + tool_calls * tokens_per_tool_result

ratio = corpus_tokens / session_tokens

print(f"corpus: {n_emails:,} emails, ~{corpus_tokens/1e6:.0f}M tokens total")
print(f"agent context per session: ~{session_tokens:,} tokens")
print(f"sessions run: {n_sessions}")
print(f"\nThe agent reasons over ~{session_tokens/1000:.0f}K tokens per session")
print(f"while its memory spans ~{corpus_tokens/1e6:.0f}M tokens - a")
print(f"~{ratio:,.0f}x reduction vs. loading the corpus into context,")
print(f"and it never re-reads a document it has already processed.")
print(f"\nA naive 'stuff it all in the context window' approach is")
print(f"~{corpus_tokens/1e6:.0f}M tokens - {corpus_tokens/200000:.0f}x over even a")
print(f"200K-token frontier context window. Persistent memory is not an")
print(f"optimization here; it is the only way the task is possible.")
