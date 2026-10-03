"""Assertions decide whether a perturbed output is CONSISTENT with the system's
own baseline behavior — the outputs it produced on the un-perturbed input.

This is where wobbly's baseline-variance control lives: `consistent` sees the
whole baseline list, so it can ignore the system's intrinsic run-to-run noise
and only report a violation when a perturbation pushes the output beyond it.
"""
from __future__ import annotations

from typing import Any, List


def _eq(a: Any, b: Any) -> bool:
    """None-safe equality; numeric-tolerant, falls back to ==."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return a == b


class Assertion:
    """Base class. `consistent(baseline, after)` returns True when `after` is
    acceptable given the system's baseline outputs on the un-perturbed input."""
    name: str = "assertion"

    def consistent(self, baseline: List[Any], after: Any) -> bool:
        raise NotImplementedError


class Unchanged(Assertion):
    """Exact: the perturbed output must equal the baseline output(s). Use for
    DETERMINISTIC systems, whose baseline is all-identical."""
    name = "unchanged"

    def consistent(self, baseline: List[Any], after: Any) -> bool:
        return all(_eq(b, after) for b in baseline)


class ConsistentPick(Assertion):
    """Discrete outputs: the perturbed output must be one the system ALSO
    produced on the clean input. A violation means the perturbation made it pick
    something outside its own clean-input flicker. The baseline-variance control
    for discrete outputs."""
    name = "consistent pick"

    def consistent(self, baseline: List[Any], after: Any) -> bool:
        return any(_eq(b, after) for b in baseline)


class ScalesBy(Assertion):
    """The output must scale by a known factor relative to the baseline."""
    name = "scales by"

    def __init__(self, factor: float, tol: float = 1e-6):
        self.factor = factor
        self.tol = tol

    def consistent(self, baseline: List[Any], after: Any) -> bool:
        if after is None:
            return all(b is None for b in baseline)
        for b in baseline:
            if b is None:
                continue
            if abs(float(after) - float(b) * self.factor) < max(self.tol, abs(float(b)) * 1e-4):
                return True
        return False


def unchanged() -> Assertion:
    return Unchanged()


def consistent_pick() -> Assertion:
    return ConsistentPick()


def scales_by(factor: float, tol: float = 1e-6) -> Assertion:
    return ScalesBy(factor, tol)
