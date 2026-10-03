"""Order / position invariance — the general hero relation.

Reordering the *independent elements* of an input (multiple-choice options,
retrieved documents, list items) must not change a correct system's output. When
it does, the system is order-sensitive — a real, label-free bug (option-order
bias; position bias / "lost in the middle").

A *shaper* tells wobbly which part of the input to permute: a named dict field, a
(get, set) accessor pair, or — by default — the whole input (when it is a list).
Permutations are seeded (reproducible) and vary across samples; with fewer than
two elements the transform abstains (returns the input unchanged).
"""
from __future__ import annotations

import hashlib
import random
from typing import Any, Callable, List, Optional

from .core import Relation
from .assertions import Assertion, consistent_pick


def _seed(elements: List[Any], salt: int) -> int:
    h = hashlib.md5(repr(elements).encode("utf-8")).hexdigest()
    return (int(h, 16) ^ (salt & 0xFFFFFFFF)) & 0xFFFFFFFF


def permute(
    getter: Callable[[Any], List[Any]],
    setter: Callable[[Any, List[Any]], Any],
    seed_offset: int = 0,
) -> Callable[[Any], Any]:
    """Return a transform that reorders the elements `getter` pulls from the
    input and rebuilds the input via `setter`. Deterministic given content; each
    successive call yields a different permutation so `samples > 1` explores
    several orderings. Abstains (no-op) when there are fewer than two elements."""
    counter = {"n": 0}

    def t(base_input: Any) -> Any:
        elements = list(getter(base_input))
        if len(elements) < 2:
            return base_input
        rng = random.Random(_seed(elements, seed_offset ^ counter["n"]))
        counter["n"] += 1
        order = list(range(len(elements)))
        rng.shuffle(order)
        return setter(base_input, [elements[i] for i in order])
    return t


def order_invariant(
    field: Optional[str] = None,
    get: Optional[Callable[[Any], List[Any]]] = None,
    set: Optional[Callable[[Any, List[Any]], Any]] = None,
    assertion: Optional[Assertion] = None,
    seed_offset: int = 0,
    name: Optional[str] = None,
) -> Relation:
    """Build an order/position-invariance Relation.

    Shaper (pick one):
      - `field="options"` — permute `base_input[field]` (dict input), other keys kept.
      - `get=..., set=...` — accessor pair for any input shape.
      - neither — `base_input` itself is the list to permute.

    `assertion` defaults to `consistent_pick()` (discrete-friendly; a perturbed
    output must be one the system also produced on the un-perturbed input).
    """
    if get is not None or set is not None:
        if get is None or set is None:
            raise ValueError("provide both get and set, or neither, or just field")
        getter, setter = get, set
        label = "the selected elements"
    elif field is not None:
        getter = lambda x, f=field: x[f]
        setter = lambda x, v, f=field: {**x, f: v}
        label = f"field '{field}'"
    else:
        getter = lambda x: x
        setter = lambda x, v: v
        label = "the input list"

    return Relation(
        name=name or f"reorder {label} => output unchanged",
        transform=permute(getter, setter, seed_offset),
        assertion=assertion if assertion is not None else consistent_pick(),
    )
