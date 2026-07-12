# Case study: the whistleblower dilemma (Vince Kaminski)

*Every fact below is pulled directly from the agent's CockroachDB memory
(`src/kaminski_study.py`) - no fabricated timelines.*

Vince Kaminski was Enron's head of Research / risk management. He is famous for
**warning against** the LJM/Raptor structures - he told management they were
improper. He was never charged. He is **not** a Person of Interest.

The agent flagged him anyway, at **0.95**. This is the project's most
instructive result, because it shows exactly what a memory-driven agent gets
right, what it gets wrong, and why the evidence store matters.

## What the agent recorded (real rows)

**Suspect score:** `0.95` with the agent's own rationale already hedging:
> "Frequently discusses SPV/Raptor structures, but as risk officer WARNING
> against them - likely whistleblower, not perpetrator (unresolved)."

**Hypotheses it built about him (real, verbatim, with status):**
- `[supported 0.95]` "...may have been involved in the systemic failure to
  document hedge designations, particularly regarding the wind hedge, which
  would have forced immediate mark-to-market accounting and exposed Enron's
  true [exposure]."
- `[supported 0.85]` "...central figure in risk and accounting coordination...
  may have been involved in the failure to properly document risk hedges..."

**What drove the 0.95** (real score-history row):
> "Confirmed evidence from a September 5, 2001 email by Wes Colwell explicitly
> states that the wind hedge's designation [was undocumented]..."

## The error, precisely

The agent conflated **"central to risk management"** with **"complicit in
concealment."** Kaminski's team touched the hedge-documentation issues *because
that was his job* - flagging and analysing risk. Proximity to the problem is
not participation in it. This is the classic investigator's trap: the person
who talks most about the fraud is often the one trying to stop it.

## What the memory store made possible

Because every signal is preserved in CockroachDB rather than collapsed into a
single score, we could run two independent post-hoc reviews against the *same*
stored evidence:

| Signal (real experiment result) | Verdict on Kaminski |
|---|---|
| **E3 - stance from his own emails** | "neutral" (0.9 conf): "routine technical discussions... without evidence of promoting, concealing, or objecting" |
| **E4 - third-party reputation** | "peripheral": "described as assisting with document retrieval and reviewing agreements, not as a wrongdoer" |

**Both reviews correctly concluded he is not a perpetrator.** Yet neither could
be safely auto-applied: E3 demoted the real culprits too (perpetrators also look
innocent in their own mail), and E4 over-demoted real POIs whose evidence is
outside this corpus. The score history literally records E3 dropping him to
`0.35` and the change being reverted.

## Why this is the point, not a bug

A naive vector store would keep one number and lose the argument. CockroachDB
keeps the **contradiction**: the flagging evidence, the exculpatory stance
signal, the reputation verdict, and the full score history side by side, joined
and queryable. That is what lets a human investigator - or a future
multi-signal scorer - see that Kaminski was *right to surface and wrong to
indict*, and understand exactly why. Preserving contradictory evidence with
provenance is the difference between a memory system and a guesser.

**Status:** Kaminski remains on the board at 0.95, flagged as `unresolved`. We
deliberately did **not** hand-correct it, because the honest state of the art -
that distinguishing "discusses fraud" from "commits fraud" is unsolved with a
local model on this corpus - is more valuable than a doctored board.
