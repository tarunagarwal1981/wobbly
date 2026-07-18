# CLAUDE.md — invar receipts demo

## CORE (load-bearing — read before changing anything)

**What this repo is.** The proof-on-real-data demo for `invar`, a metamorphic
testing library. It exists to back a public writeup (Medium/LinkedIn) and a
Show HN launch. The repo IS the receipt: `git clone && python scripts/run_blind.py`
must reproduce the headline numbers offline with no API key.

**The thesis being proven.**
> You can find wrong AI outputs without having the right answers.

Method: transform an input in ways that must not change the correct output
(reorder lines, add irrelevant footer, strip currency symbols). Run the system
on both. If the outputs disagree, the system contradicted itself — a bug found
with zero labels.

**The two-stage design is non-negotiable.** It is the entire credibility of the
piece and must not be collapsed:
- **Stage 1 (BLIND):** run invar over all receipts. Ground-truth labels are
  NEVER read. Produces a set of flagged receipts.
- **Stage 2 (AUDIT):** only now open `true_total`, purely to score whether the
  blind flags corresponded to real errors.

If any code path lets label data influence Stage 1, the demo is worthless.
Keep the separation obvious and auditable in the source.

**Honest-numbers rule.** Do not tune the extractor or the transforms to make the
statistic look better. If the honest lift is small, the article reports the small
number and explains why. The whole value of this piece against the AI-hype
background is that it doesn't lie. Tuning for a prettier number is the one
failure mode that kills it.

## The dataset

ICDAR-2019-SROIE — real scanned Malaysian receipts, public.
Source: `https://github.com/zzzDavid/ICDAR-2019-SROIE`
- `data/box/NNN.csv` — OCR lines (8 bbox coords, then the text)
- `data/key/NNN.json` — ground truth incl. `total`
- 626 receipts; 625 have a total; 535 have a clean numeric `NN.NN` total.

`data/receipts.json` in this repo is a frozen 120-receipt slice
(`{id, lines, true_total}`) so the demo runs offline. Rebuild/expand it from the
upstream clone if a larger N is wanted — 535 usable receipts are available and
a bigger N would tighten the statistic.

**Why this dataset is the right choice:** avg **13 dollar-shaped numbers per
receipt** (max 49), exactly one of which is the true total. Genuine haystack.
Totals are frequently reprinted 2–4x, and near-miss traps abound: SUBTOTAL,
TOTAL QTY, TOTAL GST, TOTAL SALES (EXCLUDING GST) vs (INCLUSIVE OF GST).

## Current state

Working and running. `python scripts/run_blind.py` executes end to end.

Last honest run (120 receipts, current code):
```
Stage 1 BLIND : 74/120 flagged (62%)
Stage 2 AUDIT : extractor wrong on 62/120 (baseline accuracy 48%)
                precision of flags 57%
                error rate flagged 57% vs not-flagged 43%  => 1.3x lift
```

Real catches confirmed, e.g. receipt `000`: extractor returns `9.0`, and under
line reordering returns a different value on the same receipt. That
contradiction is undeniable and required no answer key. **The engine works.**

## KNOWN DEFECTS — this is the open work

Two separate problems, both must be fixed before publishing. Do not conflate.

**Defect 1 — the extractor is too weak (48% baseline accuracy).**
No one ships a 48%-accurate extractor, so it reads as a strawman. Target a
realistic **~80–85%**, with residual errors concentrated in genuinely
order-sensitive cases. Known real failure modes in the data, all authentic:
- `TOTAL SALES (EXCLUDING GST)` chosen over `(INCLUSIVE OF GST)` — receipts 008, 014
- cue line and value line separated, lookahead misfires — receipt 009
- `TOTAL QTY: 1.00` — the word TOTAL attached to a quantity, not money — receipts 021, 022
- the total reprinted at the bottom, so "last cue wins" grabs a stale figure

Do NOT fix by special-casing individual receipts. Fix the cue→value association
and GST-inclusive preference as general rules.

**Defect 2 — the reorder transform is unfair.**
`reorder_lines` currently shuffles ALL lines, which destroys the cue→value
adjacency that any real extractor legitimately depends on. Under that transform
even a *correct* extractor would break, which inflates the flag rate (62%) and
craters precision. **Fix: make it block-aware** — permute semantically
independent blocks (header / line-items / totals-block / footer) while keeping
local structure intact.

This fix is also one of the most valuable *article* sections: how to design a
metamorphic relation that is strict but fair. A relation that any correct system
would fail is a bad relation, not a bug detector.

**Success criterion:** after both fixes, the audit should show a clean,
defensible gap between flagged and not-flagged error rates, with the flag rate
well below 62%. Report whatever it honestly comes out to.

## Repo layout

```
invar/core.py        check(), Relation, Report, Counterexample — the engine
invar/relations.py   the extraction relation pack (transforms + assertions)
invar/extractor.py   the system under test (stand-in for an LLM extractor)
scripts/run_blind.py the two-stage blind + audit run
data/receipts.json   frozen 120-receipt slice
```

`invar/core.py` is generic and domain-free — keep it that way. Domain knowledge
belongs in `relations.py`. The relation pack is the intended moat ("taste is the
point"); the engine is deliberately small.

## TODO

1. Fix Defect 2 (block-aware reorder) — do this FIRST; it changes all numbers.
2. Fix Defect 1 (extractor to ~80–85%) — general rules only.
3. Re-run the audit; record the honest numbers.
4. Consider expanding the frozen slice to all 535 usable receipts for a tighter stat.
5. `tests/` — pytest that asserts the demo reproduces (the `git clone && pytest` promise).
6. Optional `scripts/live_extract.py` — same relations against a real Anthropic
   API call, showing the relations catch a real LLM's real drift. Frozen path
   stays the default so the repo runs with no key.
7. Package for PyPI (the engine + pack, not the demo data).

## DOMAIN NOTES

- Money regex `(?<!\d)(\d{1,6}\.\d{2})(?!\d)` — avoids matching inside longer digit runs.
- Malaysian receipts: currency `RM`, 6% GST era, "ROUNDING ADJUSTMENT" lines common.
- Totals appear as: `TOTAL`, `TOTAL (RM)`, `ROUND TOTAL`, `TOTAL AMOUNT`,
  `TOTAL SALES (INCLUSIVE OF GST)`, `NET TOTAL`, `AMOUNT DUE`.
- Comparison tolerance: `abs(got - truth) > 0.011` counts as wrong (handles
  rounding-adjustment cents).

## Publication plan (context, not code)

Sequence: make it real → prove on real data → honest writeup → distribution.
1. Fix defects, clean numbers, tests pass.
2. Publish package to PyPI.
3. Deep Medium article (the oracle problem, the method, the real result incl.
   caveats, and the "fair relation design" lesson).
4. Show HN pointing at the reproducible repo.
5. X thread, then LinkedIn cut driving to the article.

Positioning: vertical-domain operator who actually builds and validates. The
maritime angle (physics relations on noon reports — distance ≈ speed × time,
fuel burn vs tank drop) is a strong closing callout showing the technique
generalizes, but the hero demo stays financial-docs for audience reach.
