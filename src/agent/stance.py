"""Stance detection: does a person PERPETRATE a scheme or WARN AGAINST it?

The core fix for the whistleblower trap (mistaking Kaminski, Enron's risk
chief who objected to the deals, for a culprit). Uses the local LLM to read a
person's own authored emails on the flagged topics and classify their role.
"""
import json
import os

import psycopg
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

STANCE_PROMPT = """You are analyzing an Enron employee's role. Below are
excerpts they personally WROTE about financial structures/deals. Classify
their stance:

- "perpetrator": they design, push, approve, or conceal questionable deals;
  they pressure others; they benefit and hide it.
- "whistleblower": they warn about, object to, question the legality/ethics
  of, or flag the risk of these structures.
- "neutral": they merely process, report, or discuss without a clear stance.

Respond ONLY with JSON: {"stance": "...", "confidence": 0-1, "why": "one line"}"""


KEYWORDS = ["LJM", "special purpose", "off-balance", "off balance",
            "partnership", "Raptor", "SPE", "conflict of interest",
            "restate", "hide", "conceal", "prepay"]


def author_excerpts(conn, person_id, topics, limit=6):
    """Emails this person SENT that mention the flagged topics (keyword
    filter — fast, uses the sender index; good enough for stance)."""
    like = " OR ".join("e.body ILIKE %s" for _ in KEYWORDS)
    params = [person_id] + [f"%{k}%" for k in KEYWORDS] + [limit]
    rows = conn.execute(
        f"SELECT left(e.body, 600) FROM emails e"
        f" WHERE e.sender_id=%s AND ({like})"
        f" ORDER BY e.sent_at DESC LIMIT %s", params).fetchall()
    return [r[0] for r in rows]


def classify_stance(person_id, topics=None):
    """Return {stance, confidence, why, n_excerpts} for a person."""
    topics = topics or ["special purpose entity off-book partnership LJM",
                        "hiding debt accounting", "conflict of interest"]
    conn = psycopg.connect(os.environ["CRDB_URL"])
    ex = author_excerpts(conn, person_id, topics)
    if not ex:
        return {"stance": "unknown", "confidence": 0.0,
                "why": "no authored emails on these topics", "n_excerpts": 0}
    client = OpenAI(base_url=os.environ["OLLAMA_URL"], api_key="ollama",
                    timeout=90, max_retries=1)
    msg = STANCE_PROMPT + "\n\nEXCERPTS:\n" + "\n---\n".join(
        e[:500] for e in ex)
    r = client.chat.completions.create(
        model=os.environ["AGENT_MODEL"],
        messages=[{"role": "user", "content": msg}],
        max_tokens=200, temperature=0)
    txt = r.choices[0].message.content
    try:
        start = txt.index("{")
        out = json.loads(txt[start:txt.rindex("}") + 1])
    except Exception:
        out = {"stance": "neutral", "confidence": 0.3, "why": txt[:80]}
    out["n_excerpts"] = len(ex)
    return out


if __name__ == "__main__":
    import sys
    print(classify_stance(sys.argv[1]))
