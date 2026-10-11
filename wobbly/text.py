"""Text-level fairness relations: a correct system's answer must not change when
irrelevant text is added, whitespace/formatting is altered, or the instruction is
reworded to an equivalent phrasing. All deterministic and dependency-free; each
uses `resolve_shaper` to target a dict field, an accessor, or the whole input."""
from __future__ import annotations

import hashlib
import random
from typing import Any, Callable, List, Optional

from .core import Relation
from .assertions import Assertion, consistent_pick
from ._shaping import resolve_shaper

# Content-free filler: adds LENGTH, never information. A correct system (or judge)
# must ignore it — that is what makes padding a fair metamorphic change.
_FILLER: List[str] = [
    "To put it another way, the same point still stands.",
    "It is worth restating this clearly.",
    "In other words, the above holds.",
    "This bears repeating for emphasis.",
    "Simply put, nothing here changes.",
    "As already noted, the essential idea is unchanged.",
]


def pad_text(text: str, filler: Optional[List[str]] = None, factor: float = 2.0,
             seed: int = 0) -> str:
    """Append content-free filler to `text` until it is roughly `factor`x longer.

    Deterministic for a given (text, seed). The filler adds length, not meaning —
    so a verdict that moves on padding alone is length/verbosity bias, not a real
    quality difference. (If you pass your own `filler`, keeping it content-free is
    on you.)"""
    if not isinstance(text, str) or not text:
        return text
    pool = filler or _FILLER
    rng = random.Random(int(hashlib.md5((text + "|" + str(seed)).encode("utf-8")).hexdigest(), 16) & 0xFFFFFFFF)
    target = len(text) * factor
    out = text
    guard = 0
    while len(out) < target and guard < 2000:
        out = out + " " + pool[rng.randrange(len(pool))]
        guard += 1
    return out


def length_invariant(
    field: Optional[str] = None,
    get: Optional[Callable[[Any], str]] = None,
    set: Optional[Callable[[Any, str], Any]] = None,
    assertion: Optional[Assertion] = None,
    filler: Optional[List[str]] = None,
    factor: float = 2.0,
    seed_offset: int = 0,
    name: Optional[str] = None,
) -> Relation:
    """Pad the targeted text with content-free filler. A correct system's output
    must not change just because the text got longer. Flags length/verbosity
    sensitivity (e.g. a classifier or judge that reacts to length, not content).
    Deterministic (padding is seeded by content), so it runs once per check."""
    getter, setter, label = resolve_shaper(field=field, get=get, set=set)

    def t(x: Any) -> Any:
        text = getter(x)
        if not isinstance(text, str) or not text:
            return x  # abstain: nothing to pad
        return setter(x, pad_text(text, filler=filler, factor=factor, seed=seed_offset))

    return Relation(
        name=name or f"padding {label} => output unchanged",
        transform=t,
        assertion=assertion if assertion is not None else consistent_pick(),
        deterministic=True,
    )


def distractor_robust(
    field: Optional[str] = None,
    get: Optional[Callable[[Any], str]] = None,
    set: Optional[Callable[[Any, str], Any]] = None,
    distractor: str = "By the way, the weather is nice today.",
    assertion: Optional[Assertion] = None,
    name: Optional[str] = None,
) -> Relation:
    """Append an irrelevant sentence to the text. A correct answer must not change."""
    getter, setter, label = resolve_shaper(field=field, get=get, set=set)

    def t(x: Any) -> Any:
        return setter(x, getter(x) + " " + distractor)

    return Relation(
        name=name or f"irrelevant distractor in {label} => output unchanged",
        transform=t,
        assertion=assertion if assertion is not None else consistent_pick(),
        deterministic=True,
    )


_FORMATS: List[Callable[[str], str]] = [
    lambda s: "  " + s + "  ",
    lambda s: s.replace(" ", "  "),
    lambda s: s + "\n",
    lambda s: "\n" + s + "\n",
    lambda s: "\t" + s,
]


def formatting_invariant(
    field: Optional[str] = None,
    get: Optional[Callable[[Any], str]] = None,
    set: Optional[Callable[[Any, str], Any]] = None,
    assertion: Optional[Assertion] = None,
    name: Optional[str] = None,
) -> Relation:
    """Apply whitespace/layout changes that do not change meaning. A correct
    answer must not change. Successive samples cycle through several formats."""
    getter, setter, label = resolve_shaper(field=field, get=get, set=set)
    counter = {"n": 0}

    def t(x: Any) -> Any:
        fmt = _FORMATS[counter["n"] % len(_FORMATS)]
        counter["n"] += 1
        return setter(x, fmt(getter(x)))

    return Relation(
        name=name or f"formatting of {label} => output unchanged",
        transform=t,
        assertion=assertion if assertion is not None else consistent_pick(),
    )


def paraphrase_invariant(
    field: Optional[str] = None,
    get: Optional[Callable[[Any], str]] = None,
    set: Optional[Callable[[Any, str], Any]] = None,
    variants: Optional[List[str]] = None,
    paraphrase: Optional[Callable[[str], str]] = None,
    assertion: Optional[Assertion] = None,
    name: Optional[str] = None,
) -> Relation:
    """Reword the targeted text to an equivalent phrasing. Supply `variants`
    (a list of equivalent phrasings) or `paraphrase` (a callable text->text).
    A correct answer must not change. (True auto-paraphrase via an LLM is an
    `[llm]` feature; here the equivalence is user-declared, keeping it fair.)"""
    if not variants and paraphrase is None:
        raise ValueError("paraphrase_invariant needs variants=[...] or paraphrase=callable")
    getter, setter, label = resolve_shaper(field=field, get=get, set=set)
    counter = {"n": 0}

    def t(x: Any) -> Any:
        if variants:
            new = variants[counter["n"] % len(variants)]
        else:
            new = paraphrase(getter(x))
        counter["n"] += 1
        return setter(x, new)

    return Relation(
        name=name or f"paraphrase of {label} => output unchanged",
        transform=t,
        assertion=assertion if assertion is not None else consistent_pick(),
    )
