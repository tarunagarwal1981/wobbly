# wobbly

Metamorphic testing for AI outputs — find wrong answers without an answer key.

```bash
pip install wobbly          # not yet on PyPI; until then:
pip install git+https://github.com/tarunagarwal1981/wobbly
```

Python ≥ 3.9, no dependencies.

## The problem

You point an LLM at 10,000 documents and ask it to extract a number. It returns
10,000 numbers, some of them wrong. You can't check them against ground truth —
not having ground truth is the whole reason you used a model. So the wrong ones
ship silently. Building a labelled test set costs weeks and only covers the
documents you already labelled.

`wobbly` finds wrong outputs with no labels. It uses the fact that you usually
know what *shouldn't* change the answer: reorder a receipt's lines, add an
irrelevant footer, strip currency symbols — the total must stay the same. Run
the system on the original and on each variant. If two "obviously equivalent"
inputs produce different outputs, the system just contradicted itself. That's a
bug, found without knowing the right answer.

## Quickstart

```python
import random
from wobbly import check, Relation, unchanged

# 1. Your system under test: input -> output. This total-extractor has a bug —
#    it keeps the amount on the LAST line mentioning "total", and "SUBTOTAL"
#    also contains "total", so its answer depends on the order of the lines.
def extract_total(receipt):
    total = None
    for line in receipt["lines"]:
        if "total" in line.lower():
            amounts = [w for w in line.split() if w.replace(".", "").isdigit()]
            if amounts:
                total = float(amounts[-1])
    return total

# 2. A metamorphic relation: reordering the lines must not change the total.
rng = random.Random(0)
def shuffle_lines(receipt):
    lines = list(receipt["lines"])
    rng.shuffle(lines)
    return {"lines": lines}

reorder = Relation(
    name="reorder lines => total unchanged",
    transform=shuffle_lines,
    assertion=unchanged(),
)

# 3. Run the check. No ground-truth total is ever supplied.
receipt = {"lines": ["Flat White     4.50",
                     "Muffin         3.00",
                     "SUBTOTAL       7.50",
                     "TOTAL          7.95",
                     "CASH          10.00"]}

report = check(extract_total, receipt, [reorder], samples=20)
print(report.summary())
```

Output:

```
BROKE (1 of 5 trials):
  [reorder lines => total unchanged] expected 7.95 to be preserved, got 7.5
```

The extractor returned `7.95` on the original and `7.5` on a reordering of the
same receipt. No correct total was needed to know one of those is wrong.

## Core concepts

**`Relation(name, transform, assertion, deterministic=False)`** — a metamorphic
relation. `transform` maps an input to a modified input whose effect on the
output is known; `assertion(before, after)` decides whether the two outputs are
consistent. Pass `deterministic=True` when the transform always produces the
same output for a given input (see the cost note below).

**`check(system, base_input, relations, samples=20, subject="")` → `Report`** —
runs `system` (any `input -> output` callable) on `base_input`, then on each
relation's transformed input, and checks the assertion holds. **Input contract:**
`base_input`, `system`, and every relation's `transform` must accept the same
input shape — `check` feeds each transformed input straight back into `system`.
`samples` is how many times a *randomized* relation is tried; a relation marked
`deterministic=True` runs once regardless (repeating it would only re-run your
system on identical input).

**`Report`** — the result:

| attribute | meaning |
|---|---|
| `report.broke` | `True` if any relation was violated |
| `report.counterexamples` | list of `Counterexample`, one per violated relation |
| `report.trials` | how many transform/assert cycles ran |
| `report.errors` | messages if the system raised |
| `report.summary()` | one-line human-readable result |

Each **`Counterexample`** has `.relation` (name), `.before`, `.after`, and
`.detail`. A report with `broke == False` is not proof of correctness — only
that these relations found no contradiction.

```python
if report.broke:
    c = report.counterexamples[0]
    print(c.relation, c.before, "->", c.after)   # reorder... 7.95 -> 7.5
```

## Writing your own relations

This is where the value is, and where the mistakes are. A relation is only a bug
detector if a *correct* system would pass it. A transform that a correct system
would also fail is not a strict test — it is a broken one, and it produces false
alarms that bury the real ones.

The worked example is line reordering. The naive version shuffles **all** the
lines:

```python
rng = random.Random(0)
def shuffle_lines(receipt):
    lines = list(receipt["lines"])
    rng.shuffle(lines)
    return {"lines": lines}
```

This looks reasonable — a total shouldn't depend on line order — but it is
unfair. Real extractors pair a cue with a nearby value (`TOTAL` on one line, the
amount on the next). Shuffling every line destroys that adjacency, so even a
*correct* extractor breaks. On 120 receipts this transform flagged 72; switching
to the fair version below showed 68 of those 72 flags were artifacts of the
broken transform, not real bugs.

The fix is to permute only **semantically independent blocks** — header,
line-items, totals-block, footer — as units, keeping each block's internal order
intact. A correct total cannot depend on where the footer sits relative to the
header, but it legitimately may depend on the local structure inside the totals
block. That is the fair test, and it is what ships in the built-in pack
(`wobbly/relations.py`, `reorder_lines`): the flag rate dropped from 60% (72/120)
to 3% (4/120), and what remained were genuine order-sensitivity bugs. The lesson
generalizes: **design the transform so that only a real defect can fail it.**

Assertions are just `(before, after) -> bool`. `unchanged()` requires equality;
`scales_by(factor)` requires the output to scale by a known factor (e.g. double
every quantity, expect double the total). Write your own for anything else.

If your transform always produces the same output for a given input (a fixed
footer, a currency strip), pass `deterministic=True` to `Relation` so `check`
runs it once instead of `samples` times — see [Cost](#cost).

## Built-in relation pack

A ready-made pack for a lines-in / scalar-out extractor (a receipt total, an
invoice amount, a count). Import the assemblers from `wobbly`:

| function | returns | asserts |
|---|---|---|
| `default_pack()` | `list[Relation]` | all three relations below |
| `total_reorder_invariant(seed_offset=0)` | `Relation` | block-aware reorder ⇒ output unchanged |
| `total_footer_invariant()` | `Relation` | appended footer noise ⇒ output unchanged |
| `total_currency_invariant()` | `Relation` | stripped `RM`/`$`/`USD` tokens ⇒ output unchanged |
| `unchanged()` | assertion | `before == after` (None-safe) |
| `scales_by(factor, tol=1e-6)` | assertion | `after == before * factor` |

The transforms these wrap — `reorder_lines(seed_offset=0)`,
`inject_footer(text=...)`, `normalize_currency()` — are exported at top level
too, so you can compose them into your own relations. They operate on a
`{"lines": [...]}` dict.

```python
from wobbly import check, default_pack, extract_total

receipt = {"lines": ["MINIMART SDN BHD", "Milk        5.00", "Bread       2.50",
                     "TOTAL       7.50", "CASH       10.00", "CHANGE      2.50"]}
report = check(lambda r: extract_total(r["lines"]), receipt, default_pack())
print(report.summary())        # OK — 22 trials, no contradiction found
```

`extract_total(lines)` is the demo system under test — a heuristic receipt-total
extractor, not part of the engine. Note it takes `lines`, not the receipt dict,
so it is wrapped in `lambda r: extract_total(r["lines"])` to match `check`'s
`system(input)` shape. (A "no contradiction" result is not a guarantee of
correctness — see the experiment for real catches on messier receipts.)

## Cost

Per input, `check` calls your system once for the base output, then **once for
each `deterministic` relation** and **up to `samples` times for each randomized
relation**. Deterministic transforms (a fixed footer, currency stripping) are
run once — `check` will not pay your system to re-process identical input, which
matters when the system is a paid API call. (On the built-in pack over the 535
receipts, marking the two deterministic relations cut total system calls by
~59%.) This is offline / CI / sampling work — run it over a batch or a sample of
production traffic, not as a wrapper on every live request.

## Limitations

- **High precision, low recall.** On the receipt dataset it flagged ~2% of
  receipts and caught ~8% of all extraction errors. It does not find most bugs;
  it finds bugs it can find *cheaply and with no labels*, and what it flags is
  strongly enriched for real errors. Treat it as a spot-check, not a test suite.
- **One dataset.** The evidence below is receipts (ICDAR-SROIE). The technique is
  general; the numbers are not a benchmark across domains.
- **The system under test here is a heuristic**, not a live LLM. The relations
  are model-agnostic, but the shipped demo does not call an API.
- **Small flag counts** mean the per-cohort statistics have real sampling noise;
  see the dev/held-out split below.

## The experiment

Evidence that this works on real data: an extractor run over **535 real scanned
receipts** ([ICDAR-2019-SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE)),
in two deliberately separated stages — **BLIND** (wobbly flags receipts, never
reading the labels) then **AUDIT** (labels opened only to score those flags). The
extraction rules were tuned on the first 120 receipts (DEV); the remaining 415
(HELD-OUT) were never seen during development, so they are the honest test.

| cohort | receipts | extractor accuracy | flagged | precision | error rate flagged vs not |
|---|---|---|---|---|---|
| DEV | 120 | 87% | 2 | 100% | 100% vs 12% (8.4×) |
| HELD-OUT | 415 | 72% | 11 | 73% | 73% vs 27% (2.7×) |
| COMBINED | 535 | 75% | 13 | 77% | 77% vs 23% (3.3×) |

On held-out data, receipts wobbly flagged were **2.7× more likely to be wrong**
than receipts it didn't — with zero labels used to decide the flags. The 15-point
DEV→HELD-OUT accuracy drop is the real generalization gap, reported openly.

Reproduce it (offline, no API key):

```bash
python scripts/run_blind.py              # the table above
pip install -e ".[test]" && pytest       # pins these numbers; asserts Stage 1 is blind
```

The frozen slice in `data/receipts.json` is regenerable from upstream, which
proves it wasn't cherry-picked:

```bash
python scripts/build_receipts.py --upstream <ICDAR-2019-SROIE clone>
# rebuilds the 535 by the stated filter and asserts byte-identity to the
# committed file; WOBBLY_SROIE=<clone> pytest runs the same check as a test.
```

## Related work

Metamorphic testing is a well-established idea, and applying it to ML/LLM systems
is an active area — see **METAL** (a metamorphic testing framework for LLMs),
**LLMorph** ([arXiv:2603.23611](https://arxiv.org/abs/2603.23611)), and
**[Giskard](https://github.com/Giskard-AI/giskard)** for LLM/ML testing. `wobbly`
is not novel research; it is a small, focused engine (`check` + `Relation` +
`Report`, a few hundred lines) plus an opinionated relation pack, built to make
the technique easy to apply to your own extraction system.

## License

MIT.
