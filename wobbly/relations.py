"""Relation pack for structured extraction from documents.

These are the metamorphic relations that must hold for ANY correct extractor
that pulls a scalar (a total, an amount, a count) out of a list of text lines.
They need no ground truth — they assert consistency of the extractor with
itself under input changes that a correct extractor must be immune to.

This pack is the reusable, opinionated part: it encodes which transforms
actually surface real production bugs in extraction systems.
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Any, Callable, List, Tuple

from .core import Relation

# Money value, per the domain notes: NN.NN not embedded in a longer digit run.
_MONEY = re.compile(r"(?<!\d)(\d{1,6}\.\d{2})(?!\d)")

# Keywords that mark the totals / payment region of a receipt. These are the
# lines whose *relative* order to the rest of the receipt must not matter, but
# whose *internal* cue->value adjacency a correct extractor legitimately relies
# on. Deliberately broad (covers subtotal, tax, tender, change, rounding) so the
# whole totals block is captured as one unit.
_TOTALS_CUES = (
    "TOTAL", "SUBTOTAL", "SUB-TOTAL", "SUB TOTAL",
    "GST", "TAX", "ROUNDING", "ROUND",
    "AMOUNT", "CASH", "CHANGE", "CARD", "VISA", "MASTER",
    "PAID", "PAYMENT", "TENDER", "BALANCE", "DUE",
)

# ---- assertions -------------------------------------------------------------

def _eq(a: Any, b: Any) -> bool:
    # None-safe equality; two Nones are "consistent" (both abstained)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < 1e-6


def unchanged() -> Callable[[Any, Any], bool]:
    """The output must be identical before and after the transform."""
    return _eq


def scales_by(factor: float, tol: float = 1e-6) -> Callable[[Any, Any], bool]:
    """The output must scale by a known factor."""
    def ok(before: Any, after: Any) -> bool:
        if before is None or after is None:
            return before is None and after is None
        return abs(float(after) - float(before) * factor) < max(tol, abs(before) * 1e-4)
    return ok


# ---- transforms (operate on a receipt dict: {"lines": [...], ...}) ----------

def _clone(receipt: dict) -> dict:
    r = dict(receipt)
    r["lines"] = list(receipt["lines"])
    return r


def _stable_seed(lines: List[str], salt: int) -> int:
    """Deterministic seed from line content — reproducible across processes.

    (Python's built-in hash() is per-process randomized, which would make the
    reorder relation non-reproducible; the demo must reproduce offline.)
    """
    h = hashlib.md5(("\n".join(lines)).encode("utf-8")).hexdigest()
    return (int(h, 16) ^ (salt & 0xFFFFFFFF)) & 0xFFFFFFFF


def _segment_blocks(lines: List[str]) -> List[Tuple[str, List[str]]]:
    """Split receipt lines into ordered semantic blocks, no per-receipt casing:

        header       — store/meta lines above the first priced line
        line-items   — priced lines up to the totals region
        totals-block — first through last totals/payment cue line (with value)
        footer       — anything below the totals region

    The point is fairness: a correct total must not depend on where these blocks
    sit relative to each other, but it *may* depend on the local structure
    (cue->value adjacency) *within* the totals block. So we treat each block as
    an atomic unit and never disturb the lines inside it.

    Returns blocks in original order. If no totals region can be located, returns
    a single "all" block so the caller abstains rather than shuffle unfairly.
    """
    n = len(lines)
    up = [ln.upper() for ln in lines]
    is_cue = [any(c in up[i] for c in _TOTALS_CUES) for i in range(n)]
    money = [bool(_MONEY.search(lines[i])) for i in range(n)]

    # A totals line = a cue word sitting next to a money value. Requiring an
    # adjacent value keeps header noise ("GST REG NO: 000123456789", which has
    # no NN.NN amount) out of the totals region.
    def near_money(i: int) -> bool:
        return money[i] or (i + 1 < n and money[i + 1]) or (i - 1 >= 0 and money[i - 1])

    totals_idx = [i for i in range(n) if is_cue[i] and near_money(i)]
    if not totals_idx:
        return [("all", list(lines))]

    t_start, t_end = min(totals_idx), max(totals_idx) + 1
    # Absorb a trailing bare-money line that is the value for the last cue
    # (cue on one line, amount on the next), so the pair is never split.
    if t_end < n and money[t_end] and not is_cue[t_end]:
        t_end += 1

    # header | line-items boundary: the first priced line before the totals.
    items_start = next((i for i in range(t_start) if money[i]), t_start)

    blocks: List[Tuple[str, List[str]]] = []
    if items_start > 0:
        blocks.append(("header", list(lines[0:items_start])))
    if t_start > items_start:
        blocks.append(("line-items", list(lines[items_start:t_start])))
    blocks.append(("totals-block", list(lines[t_start:t_end])))
    if t_end < n:
        blocks.append(("footer", list(lines[t_end:n])))
    return blocks


def reorder_lines(seed_offset: int = 0) -> Callable[[dict], dict]:
    """Permute semantically independent BLOCKS, not individual lines.

    Shuffling every line destroys the cue->value adjacency any real extractor
    legitimately depends on, so an all-lines shuffle would fail even a *correct*
    extractor — a bad metamorphic relation. Instead we segment the receipt into
    header / line-items / totals-block / footer and permute the order of those
    blocks while keeping each block's internal structure intact. A correct total
    is invariant to block order; only genuine order-sensitivity (e.g. a stale
    total reprinted in the footer that "last cue wins" then grabs) survives.

    Each successive call returns a different block permutation, so `samples > 1`
    explores several orderings. Fully deterministic given the receipt content.
    """
    counter = {"n": 0}

    def t(receipt: dict) -> dict:
        r = _clone(receipt)
        blocks = _segment_blocks(r["lines"])
        if len(blocks) < 2:
            return r  # nothing independent to permute — abstain (fair no-op)
        rng = random.Random(_stable_seed(r["lines"], seed_offset ^ counter["n"]))
        counter["n"] += 1
        order = list(range(len(blocks)))
        rng.shuffle(order)
        r["lines"] = [ln for k in order for ln in blocks[k][1]]
        return r
    return t


def inject_footer(text: str = "THANK YOU PLEASE COME AGAIN") -> Callable[[dict], dict]:
    """Append irrelevant footer noise. Must not change the extracted total."""
    def t(receipt: dict) -> dict:
        r = _clone(receipt)
        r["lines"] = r["lines"] + [text, "*** ***", "0.00"]
        return r
    return t


def normalize_currency() -> Callable[[dict], dict]:
    """Strip 'RM'/'$' currency tokens and extra spaces. Total must not change."""
    def t(receipt: dict) -> dict:
        r = _clone(receipt)
        r["lines"] = [re.sub(r"\b(RM|USD|\$)\b", "", ln).strip() for ln in r["lines"]]
        return r
    return t


# ---- ready-made Relations for a lines-in / total-out extractor --------------

def total_reorder_invariant(seed_offset: int = 0) -> Relation:
    return Relation(
        name="reorder lines => total unchanged",
        transform=reorder_lines(seed_offset),
        assertion=unchanged(),
    )


def total_footer_invariant() -> Relation:
    return Relation(
        name="irrelevant footer => total unchanged",
        transform=inject_footer(),
        assertion=unchanged(),
    )


def total_currency_invariant() -> Relation:
    return Relation(
        name="currency normalization => total unchanged",
        transform=normalize_currency(),
        assertion=unchanged(),
    )


def default_pack() -> List[Relation]:
    """The standard invariants a receipt-total extractor must satisfy."""
    return [
        total_reorder_invariant(),
        total_footer_invariant(),
        total_currency_invariant(),
    ]
