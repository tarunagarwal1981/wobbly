"""Resolve which part of an input a relation targets: a dict field, an accessor
pair, or the whole input. Shared by all general relations so shaping is defined
in exactly one place."""
from __future__ import annotations

from typing import Any, Callable, Optional, Tuple


def resolve_shaper(
    field: Optional[str] = None,
    get: Optional[Callable[[Any], Any]] = None,
    set: Optional[Callable[[Any, Any], Any]] = None,
) -> Tuple[Callable[[Any], Any], Callable[[Any, Any], Any], str]:
    """Return (getter, setter, label).

    - field="x" -> getter x["x"], setter returns {**x, "x": v} (other keys kept)
    - get=,set= -> accessor pair (both or neither)
    - neither   -> the input itself is the target
    """
    if get is not None or set is not None:
        if get is None or set is None:
            raise ValueError("provide both get and set, or neither, or just field")
        return get, set, "the selected part"
    if field is not None:
        return (
            (lambda x, f=field: x[f]),
            (lambda x, v, f=field: {**x, f: v}),
            f"field '{field}'",
        )
    return (lambda x: x), (lambda x, v: v), "the input"
