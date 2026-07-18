"""A receipt-total extractor — the kind of thing you'd actually ship.

This stands in for an LLM (or an LLM+regex) doing structured extraction. It is
deliberately *realistic*, not a strawman. It gets the majority of real receipts
right, using the same cues a decent extraction prompt would rely on:

  - look for TOTAL-style cues, ignoring SUBTOTAL / QTY / GST-line traps,
  - read the money value on (or just after) the cue line,
  - prefer the value associated with the *last* strong total cue.

That "last strong cue wins" tie-break is a real, common heuristic — and it hides
a subtle failure: on receipts with several total-like lines (SUBTOTAL, TOTAL
SALES EXCL GST, TOTAL INCL GST, and the total reprinted at the bottom), the
answer can depend on the ORDER the lines arrive in. A correct extractor's total
must not depend on line order. That is the invariant `invar` tests — with no
answer key.

Nothing here reads the ground-truth label.
"""
from __future__ import annotations
import re
from typing import List, Optional

MONEY = re.compile(r"(?<!\d)(\d{1,6}\.\d{2})(?!\d)")

# strong signals that a line names the final payable total
STRONG_CUES = ("TOTAL", "AMOUNT DUE", "GRAND TOTAL", "NET TOTAL", "AMOUNT PAYABLE")
# lines that contain 'total' but are NOT the payable total
TRAP_CUES = (
    "SUBTOTAL", "SUB TOTAL", "SUB-TOTAL",
    "TOTAL QTY", "TOTAL QUANTITY", "QTY",
    "TOTAL GST", "GST", "TOTAL TAX", "TAX TOTAL",
    "TOTAL SALES (EXCLUDING", "TOTAL SALES (EXCL", "EXCLUDING GST", "EXCL GST",
    "TOTAL SAVINGS", "TOTAL DISCOUNT", "ITEM",
)


def _money_in(line: str) -> Optional[float]:
    m = MONEY.findall(line)
    if not m:
        return None
    return float(m[-1])


def _is_trap(line_upper: str) -> bool:
    return any(t in line_upper for t in TRAP_CUES)


def extract_total(lines: List[str]) -> Optional[float]:
    """Return the extracted receipt total, or None.

    Realistic heuristic:
      1. Walk lines in order.
      2. On a STRONG total cue that is not a trap, capture the money value on
         that line, else on the next non-empty line.
      3. Keep the value from the LAST such cue (the 'last strong cue wins'
         tie-break) — this is where order-sensitivity enters.
    """
    candidate: Optional[float] = None
    for i, raw in enumerate(lines):
        line = raw.upper()
        if _is_trap(line):
            continue
        if any(cue in line for cue in STRONG_CUES):
            val = _money_in(line)
            if val is None:
                # look ahead to the next line that carries money
                for j in range(i + 1, min(i + 3, len(lines))):
                    val = _money_in(lines[j])
                    if val is not None:
                        break
            if val is not None:
                candidate = val
    if candidate is not None:
        return candidate
    # fallback: largest money value present
    all_vals = [float(x) for l in lines for x in MONEY.findall(l)]
    return max(all_vals) if all_vals else None
