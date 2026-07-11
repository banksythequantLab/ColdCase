# Cold Case — Experiment Log

Honest record of what we tried, what worked, and what didn't. Judges asked
for insight into agentic systems; the failures are as instructive as the wins.

## E1. Recall tuning via "breadth-over-depth" prompting — WORKED

Adding explicit rules to (a) not re-investigate already-scored people and
(b) chase specific unexplored names via the LJM/partnership email trail lifted
recall from 3/18 to 4/18 and surfaced **Michael Kopper** (Fastow's lieutenant,
a real POI) purely through the communication graph and email content — not the
financial features, where he is invisible. Precision@5 rose to 80%.

## E2. "Quiet-money" financial signal — PARTIAL

Exposing `loan_advances` and email volume with a `quiet_money` flag correctly
highlights actors with large payouts but little email (Lay, Frevert). It did
NOT surface Andrew Fastow, because — contrary to our initial assumption — his
$81M+ was made off-book through the LJM partnerships and does not appear in the
Enron financial-features dataset. Fastow is financially invisible here and is
only reachable through others' emails about LJM. Correcting this assumption was
itself a useful finding.

## E3. Stance-based self-critique pass — FAILED (instructive)

**Hypothesis:** the agent's false positives (e.g. Vince Kaminski, Enron's risk
chief who *warned against* the deals) could be fixed by classifying each
suspect's stance from their own emails — perpetrator vs whistleblower vs
neutral — and demoting anyone who isn't a perpetrator.

**Result:** the pass demoted *everyone*, including the correct POIs (Skilling,
Lay, Hirko, Kopper), all of whom read as "neutral" or had no
keyword-matching authored emails.

**Why it failed — the real insight:** perpetrators and whistleblowers both look
innocent in their own outgoing mail. The perpetrator is careful and never
writes down the crime; the whistleblower's specific objections are sparse and
easily missed. The actual evidence against real fraudsters lives in *other
people's* emails about them, in third-party disclosures (e.g. the news article
detailing Lay's $80M severance), and in the financial data — not in their own
words. Stance-from-self-authored-text is therefore too weak a signal to safely
adjust scores, and applying it as a blanket rule destroys the good signal.

**Takeaway for agentic memory:** an agent's confidence should be grounded in
externally-corroborated evidence (what others say + hard financial facts),
which is exactly what the CockroachDB-backed evidence store preserves. Judging
a person by their own carefully-curated output is what a naive system does.
The pass is retained in `src/agent/review_pass.py` as a documented experiment;
it is NOT part of the production scoring path.

## Open problem

Distinguishing "discusses fraud" from "commits fraud" remains unsolved with
local models on self-authored text alone. A promising next direction is
*third-party stance*: classify what OTHERS say about a person (accusatory,
deferential, warning) rather than what they say themselves.
