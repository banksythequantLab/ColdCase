"""Reputation-based review — the E3 follow-up done right.

E3 failed because it judged suspects by their OWN mail (perpetrators and
whistleblowers both look innocent there). This judges them by what OTHERS wrote
about them: if no third party describes a suspect directing/concealing fraud,
and they're only ASSOCIATED or WARNING, cap the score. Targets false positives
(Kaminski = risk officer who warned; Lavorato = association) without touching
suspects with real third-party accusatory evidence.

Usage: python src/agent/reputation_review.py [--apply]
Default is dry-run (prints verdicts, changes nothing).
"""
import json
import os
import sys

import psycopg
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(__file__))
import tools as T

load_dotenv()
CAP = 0.4

PROMPT = """Below are excerpts written by OTHER people (not the subject) that
mention {name}. Based ONLY on how third parties describe this person, classify:
- "principal": others describe them directing, approving, structuring, or
  concealing questionable deals; named by investigators/press as a culprit.
- "peripheral": merely associated, mentioned in passing, cc'd, or described as
  warning about / questioning / analyzing risk — not as a wrongdoer.
Respond ONLY JSON: {{"role":"principal|peripheral","confidence":0-1,"why":"one line"}}"""


def classify(name, surname):
    ex = T.reputation(surname, k=8)
    if not ex:
        return {"role": "peripheral", "confidence": 0.3,
                "why": "no third-party mentions", "n": 0}
    body = "\n---\n".join(f"[by {e['written_by']}] {e['excerpt'][:400]}"
                          for e in ex)
    client = OpenAI(base_url=os.environ["OLLAMA_URL"], api_key="ollama",
                    timeout=90, max_retries=1)
    r = client.chat.completions.create(
        model=os.environ["AGENT_MODEL"], temperature=0, max_tokens=180,
        messages=[{"role": "user",
                   "content": PROMPT.format(name=name) + "\n\n" + body}])
    txt = r.choices[0].message.content
    try:
        out = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    except Exception:
        out = {"role": "peripheral", "confidence": 0.3, "why": txt[:80]}
    out["n"] = len(ex)
    return out


def main(apply=False):
    admin = psycopg.connect(os.environ["CRDB_ADMIN_URL"], autocommit=True)
    mc = admin.execute("SELECT case_id FROM investigations"
                       " WHERE title NOT LIKE 'ablation%' ORDER BY created_at"
                       " LIMIT 1").fetchone()[0]
    flagged = admin.execute(
        "SELECT p.person_id::STRING, coalesce(p.real_name,p.full_name),"
        " s.suspicion_score FROM suspects s JOIN persons p USING (person_id)"
        " WHERE s.case_id=%s AND s.suspicion_score>=0.5"
        " ORDER BY s.suspicion_score DESC", (mc,)).fetchall()
    for pid, name, score in flagged:
        surname = name.split()[0]
        v = classify(name, surname)
        keep = v["role"] == "principal"
        tag = "KEEP  " if keep else "DEMOTE"
        print(f"{tag} {name:<22} {score:.2f} -> "
              f"{score if keep else min(score,CAP):.2f}  [{v['role']}] "
              f"{v['why'][:70]}", flush=True)
        if apply and not keep:
            new = min(score, CAP)
            rat = (f"Reputation review: third parties describe as "
                   f"'{v['role']}' ({v['why'][:80]}). Capped {score:.2f}"
                   f"->{new:.2f}.")
            admin.execute("UPDATE suspects SET suspicion_score=%s,rationale=%s,"
                          "updated_at=now() WHERE case_id=%s AND person_id=%s",
                          (new, rat, mc, pid))
            admin.execute("INSERT INTO suspect_events (case_id,person_id,"
                          "suspicion_score,rationale) VALUES (%s,%s,%s,%s)",
                          (mc, pid, new, rat))


if __name__ == "__main__":
    main("--apply" in sys.argv)
