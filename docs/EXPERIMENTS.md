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

## E4. Third-party reputation review — PARTIAL (the E3 follow-up)

**Hypothesis:** E3 failed because it read a suspect's OWN mail. Judge them
instead by what OTHERS wrote about them (`reputation` tool): keep "principals"
(described as directing/concealing), demote "peripheral" people (associated or
merely warning).

**Result (dry-run over the 7 flagged suspects):**

| suspect | verdict | correct? |
|---|---|---|
| Skilling | principal (keep) | ✅ real POI |
| Kopper | principal (keep) | ✅ real POI |
| Kaminski | peripheral (demote) | ✅ true false-positive fixed |
| Lavorato | peripheral (demote) | ✅ true false-positive fixed |
| Lay | peripheral (demote) | ❌ real POI, over-demoted |
| Hirko | peripheral (demote) | ❌ real POI, over-demoted |

**Why it's partial:** the signal is clearly meaningful — it correctly kept both
unambiguous principals and correctly caught *both* false positives. But it
over-demotes real POIs (Lay, Hirko) whose third-party accusatory evidence isn't
present in this email corpus (Lay's culpability is mostly in financial records
and press; Hirko's crimes were in Broadband, barely represented here). So
applying it blindly would be net-negative (it would drop Lay and Hirko from the
board). We therefore **keep it dry-run only** (`reputation_review.py`, no
`--apply` in the pipeline) and leave the board unchanged.

**Takeaway:** reputation is a strong *input* to the agent's live reasoning
(which is why the `reputation` tool and corroboration rule are part of the
investigation loop), but no single automated signal is safe as a blunt
post-hoc re-score. Robust scoring needs to *combine* signals — reputation,
financial anomalies, finding strength, graph position — weighted by corpus
coverage. That combination is the real open problem, and it's exactly what a
persistent, multi-signal memory store like CockroachDB is built to support.


## E5. Recall plateau - the agent is conservative by design

After ~45 sessions recall stabilises at **4/18** with **100% precision@3** and
no new false positives. In the later sessions the agent is now autonomously
investigating the *correct* remaining POIs - it looks up **Mark Koenig** and
**Paula Rieker** (both real Enron convictions) - but declines to add them to
the board because it cannot find sufficient concealment evidence in the email
corpus to cross the 0.5 threshold.

This is the intended precision/recall tradeoff, not a bug: the concealment gate
and corroboration rule stop the agent flagging people on association or thin
circumstantial evidence. Many of the 18 labelled POIs (Fastow, Koenig, Rieker)
have little incriminating content in *this* email corpus - their culpability
lives in financial filings, testimony, and press. An agent that flagged them
anyway would be guessing.

**Takeaway:** recall here is bounded by corpus coverage and a deliberately high
evidence bar, not by the memory architecture. Raising it without wrecking
precision needs richer sources (filings, testimony) joined to the email memory
- exactly the multi-source, transactional workload CockroachDB is built for.
