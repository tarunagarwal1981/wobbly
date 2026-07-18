"""A receipt-total extractor — the kind of thing you'd actually ship.

This stands in for an LLM (or an LLM+regex) doing structured extraction. It is
deliberately *realistic*, not a strawman — it gets ~87% of real receipts right,
using the same cues a decent extraction prompt would rely on:

  - look for TOTAL-style cues, ignoring SUBTOTAL / QTY / GST-line traps,
  - read the money value on (or just after) the cue line,
  - prefer the GST-INCLUSIVE / rounded / grand / amount-due total (the payable
    figure) over a bare "TOTAL", which often just reprints the exclusive
    subtotal; among equal cues, the last (final printed) figure wins.

That is a reasonable, common heuristic — yet it still hides a subtle failure: on
messy real OCR where a cue and its value land in *separate columns* (label run
here, amount run there), the value the extractor pairs with "TOTAL" can depend on
the ORDER the lines arrive in. A correct extractor's total must not depend on
line order. That residual order-sensitivity is the invariant `invar` tests — and
catches (e.g. receipts 009, 026) with no answer key.

Nothing here reads the ground-truth label.
"""
from __future__ import annotations
import re
from typing import List, Optional

MONEY = re.compile(r"(?<!\d)(\d{1,6}\.\d{2})(?!\d)")

# strong signals that a line names the final payable total
STRONG_CUES = ("TOTAL", "AMOUNT DUE", "GRAND TOTAL", "NET TOTAL", "AMOUNT PAYABLE")
# On a GST receipt the *payable* amount is the GST-INCLUSIVE total (equivalently
# the rounded/net/grand/amount-due final). A bare "TOTAL" is weaker: it often
# reprints the GST-EXCLUSIVE subtotal at the bottom of the receipt. These cues
# therefore outrank a bare "TOTAL", and — although they mention GST — they must
# not be discarded by the GST trap below.
FINAL_CUES = (
    "INCLUSIVE", "INCL",                       # "TOTAL SALES (INCLUSIVE OF GST)"
    "GRAND TOTAL", "NET TOTAL", "ROUND TOTAL",
    "AMOUNT DUE", "AMOUNT PAYABLE", "AFTER ADJ",
)
# lines that contain 'total' but are NOT the payable total
TRAP_CUES = (
    "SUBTOTAL", "SUB TOTAL", "SUB-TOTAL",
    "TOTAL QTY", "TOTAL QUANTITY", "QTY",
    "TOTAL GST", "GST", "TOTAL TAX", "TAX TOTAL",
    "EXCLUD", "EXCL GST", "EXCL. GST", "EXCLUSIVE",   # GST-exclusive subtotal
    "TOTAL SAVINGS", "TOTAL DISCOUNT", "ITEM",
)


def _money_in(line: str) -> Optional[float]:
    m = MONEY.findall(line)
    if not m:
        return None
    return float(m[-1])


def _is_final(line_upper: str) -> bool:
    """A cue that names the actual payable amount (GST-inclusive / rounded)."""
    return any(k in line_upper for k in FINAL_CUES)


def _is_trap(line_upper: str) -> bool:
    # A GST-INCLUSIVE total mentions GST but IS the payable total, so the GST/tax
    # traps must not fire on it. (This is the single biggest real failure mode:
    # "TOTAL SALES (INCLUSIVE OF GST)" was being thrown away as a GST line.)
    if _is_final(line_upper) and ("TOTAL" in line_upper or "AMOUNT" in line_upper):
        return False
    return any(t in line_upper for t in TRAP_CUES)


# A rounding adjustment moves the total by at most one 5-sen step, so a bare
# "TOTAL" within this of the inclusive figure is the *rounded* payable, whereas a
# stale GST-exclusive reprint differs by a whole GST delta (much larger).
ROUND_STEP = 0.05


def extract_total(lines: List[str]) -> Optional[float]:
    """Return the extracted receipt total, or None.

    Realistic heuristic:
      1. Walk lines in order; collect every non-trap STRONG total cue with the
         money value on it (or on the next line that carries money), tagging
         whether it is a 'final' cue (GST-inclusive / rounded / grand / due).
      2. Prefer the last 'final' cue's value — the actual payable — over a bare
         "TOTAL", which often just reprints the GST-exclusive subtotal.
      3. Exception for rounding: a bare "TOTAL" printed after the inclusive
         figure and within one rounding step of it IS the rounded payable, so it
         wins. (A stale exclusive reprint differs by a full GST delta and does
         not.) With no 'final' cue at all, fall back to the last bare "TOTAL".
    """
    cues = []  # (index, value, is_final)
    for i, raw in enumerate(lines):
        line = raw.upper()
        if _is_trap(line):
            continue
        if not any(cue in line for cue in STRONG_CUES):
            continue
        val = _money_in(raw)
        if val is None:
            # look ahead to the next line that carries money
            for j in range(i + 1, min(i + 3, len(lines))):
                val = _money_in(lines[j])
                if val is not None:
                    break
        if val is None:
            continue
        cues.append((i, val, _is_final(line)))

    finals = [(i, v) for (i, v, f) in cues if f]
    if finals:
        fi, fv = finals[-1]                      # the inclusive / rounded final
        rounded = [v for (i, v, f) in cues
                   if not f and i > fi and abs(v - fv) <= ROUND_STEP]
        return rounded[-1] if rounded else fv
    plains = [v for (i, v, f) in cues if not f]
    if plains:
        return plains[-1]                        # last bare "TOTAL"
    # fallback: largest money value present
    all_vals = [float(x) for l in lines for x in MONEY.findall(l)]
    return max(all_vals) if all_vals else None
