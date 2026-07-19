# CLAUDE.md — wobbly receipts demo

Contributor context for the proof-on-real-data demo behind `wobbly`, a
metamorphic testing library. Read this before changing anything.

## What this repo is

The demo that proves `wobbly` on real data. The repo IS the evidence:
`git clone && python scripts/run_blind.py` reproduces the headline numbers
offline, with no API key.

**The thesis being proven.**
> You can find wrong AI outputs without having the right answers.

Method: transform an input in ways that must not change the correct output
(reorder lines, add an irrelevant footer, strip currency symbols). Run the
system on both. If the outputs disagree, the system contradicted itself — a bug
found with zero labels.

## The two-stage design is non-negotiable

It is the entire credibility of the demo and must not be collapsed:
- **Stage 1 (BLIND):** run wobbly over all receipts. Ground-truth labels are
  NEVER read. Produces a set of flagged receipts.
- **Stage 2 (AUDIT):** only now open `true_total`, purely to score whether the
  blind flags corresponded to real errors.

If any code path lets label data influence Stage 1, the demo is worthless. Keep
the separation obvious and auditable in the source.

## Honest-numbers rule

Do not tune the extractor or the transforms to make the statistic look better.
If the honest lift is small, report the small number and explain why. The whole
value of this demo against the AI-hype background is that it doesn't lie. Tuning
for a prettier number is the one failure mode that kills it. In particular,
never special-case individual receipts — fix general rules only, and report
whatever the honest run gives (including a weak result).

## The dataset

ICDAR-2019-SROIE — real scanned Malaysian receipts, public.
Source: `https://github.com/zzzDavid/ICDAR-2019-SROIE`
- `data/box/NNN.csv` — OCR lines (8 bbox coords, then the text)
- `data/key/NNN.json` — ground truth incl. `total`
- 626 receipts upstream.

`data/receipts.json` is a frozen slice of **535 receipts** (`{id, lines,
true_total}`) so the demo runs offline. Filter (documented in and enforced by
`scripts/build_receipts.py`): a receipt is kept iff its `total` is a clean
`NN.NN` value (no currency prefix, no thousands comma) AND its box file yields
≥ 5 lines — 626 → 535. Records are sorted by id; the first 120 are the DEV
cohort the extraction rules were tuned on, the remaining 415 are held-out.
`scripts/build_receipts.py --upstream <clone>` rebuilds the slice from upstream
and asserts byte-identity to the committed file (opt-in; not on the offline
path).

**Why this dataset:** avg **13 dollar-shaped numbers per receipt** (max 49),
exactly one of which is the true total. Genuine haystack. Totals are frequently
reprinted 2–4x, and near-miss traps abound: SUBTOTAL, TOTAL QTY, TOTAL GST,
TOTAL SALES (EXCLUDING GST) vs (INCLUSIVE OF GST).

## Repo layout

```
wobbly/core.py             check(), Relation, Report, Counterexample — the engine
wobbly/relations.py        the extraction relation pack (transforms + assertions)
wobbly/extractor.py        the system under test (stand-in for an LLM extractor)
scripts/run_blind.py       the two-stage blind + audit run (DEV / HELD-OUT / COMBINED)
scripts/build_receipts.py  rebuild + byte-verify the frozen slice from upstream
data/receipts.json         the frozen 535-receipt slice
tests/                     pytest: demo reproduces offline + slice is regenerable
```

`wobbly/core.py` is generic and domain-free — keep it that way. Domain knowledge
belongs in `relations.py` and `extractor.py`. The relation pack is the intended
moat ("taste is the point"); the engine is deliberately small.

## Domain notes

- Money regex `(?<!\d)(\d{1,6}\.\d{2})(?!\d)` — avoids matching inside longer digit runs.
- Malaysian receipts: currency `RM`, 6% GST era, "ROUNDING ADJUSTMENT" lines common.
- Totals appear as: `TOTAL`, `TOTAL (RM)`, `ROUND TOTAL`, `TOTAL AMOUNT`,
  `TOTAL SALES (INCLUSIVE OF GST)`, `NET TOTAL`, `AMOUNT DUE`.
- The payable amount is the GST-INCLUSIVE total; a bare `TOTAL` often reprints
  the GST-exclusive subtotal. A rounding adjustment moves the final by ≤ one
  5-sen step (≤ 0.05); a stale exclusive reprint differs by a whole GST delta.
- Comparison tolerance: `abs(got - truth) > 0.011` counts as wrong (handles
  rounding-adjustment cents).
```
