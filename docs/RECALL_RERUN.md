# Recall Re-run: does adding the SEC filings lift recall?

**Experiment.** After ingesting 22 Enron SEC filings (10-K, proxy, the Nov-2001
restatement 8-K) into CockroachDB and giving the agent a `search_filings` tool,
we re-ran the autonomous investigation and re-scored against the sealed POI
labels. The question: does the agent now catch **Andrew Fastow** — the CFO and
LJM architect it had been missing from email alone?

**Result — recall held, no lift.**

| Metric | Before filings | After re-run |
|---|---|---|
| precision@3 | 100% | 100% |
| precision@5 | 80% | 80% |
| recall vs 18 POIs | 4/18 (22%) | **4/18 (22%)** |

The agent re-confirmed Skilling, Lay, Kopper, and Hirko. Fastow was **not**
surfaced — 0 suspect events on any Fastow identity across the re-run.

## Why Fastow is structurally hard (the honest finding)

This is not primarily an agent-reasoning failure — it is a property of the
corpus and of entity resolution:

1. **He is nearly invisible as an email sender.** The POI-labeled record
   `FASTOW ANDREW S` has **9 sent emails**; his `@enron.com` aliases have **0
   sent** each. (The higher-volume `lfastow@…` address is *Lea* Fastow, his
   wife.) An email-driven investigator has almost no signal on him.
2. **His guilt lives in the filings under "LJM" / "Related Party," rarely under
   his name.** Our LLM extraction pulled the real self-dealing events —
   "Related Party acquired $371M in assets from Enron," "LJM2 acquired dark
   fiber," "$36M put-option loss" — but bridging *LJM/Related Party → Andrew
   Fastow* is a reasoning leap the autonomous agent did not make.
3. **His identity is fragmented** across 7 person records; the POI label and the
   financial profile sit on `FASTOW ANDREW S`, while his corporate email aliases
   are separate records. Even a hit on an alias would not register as the POI.

## Interpretation

Cold Case is deliberately **precision-over-recall** — the cost of a false public
accusation is asymmetric, so it flags only well-corroborated actors. This re-run
shows the recall ceiling at 4/18 is set largely by the **corpus** (email-centric,
Fastow-sparse) rather than by the agent's competence: on the four POIs with real
email footprints it scores 0.99.

**Not pursued (by design decision):** we chose to report this honestly rather
than force the number up. Two legitimate paths would lift recall and are noted
as future work:
- **Entity resolution:** link Andrew Fastow's corporate aliases to his canonical
  record so a hit registers.
- **Filings-driven hypothesis seeding:** have the agent treat "Related Party /
  LJM" in the filings as a first-class lead and resolve it to a custodian.

The result stands as measured: **4/18, honestly.**
