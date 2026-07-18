"""Relation pack for structured extraction from documents.

These are the metamorphic relations that must hold for ANY correct extractor
that pulls a scalar (a total, an amount, a count) out of a list of text lines.
They need no ground truth — they assert consistency of the extractor with
itself under input changes that a correct extractor must be immune to.

This pack is the reusable, opinionated part: it encodes which transforms
actually surface real production bugs in extraction systems.
"""
from __future__ import annotations

import random
import re
from typing import Any, Callable, List

from .core import Relation

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


def reorder_lines(seed_offset: int = 0) -> Callable[[dict], dict]:
    """Shuffle the OCR line order. A correct total does not depend on order."""
    def t(receipt: dict) -> dict:
        r = _clone(receipt)
        rng = random.Random(hash((tuple(r["lines"]), seed_offset)) & 0xFFFFFFFF)
        rng.shuffle(r["lines"])
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
