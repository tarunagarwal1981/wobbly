"""Point wobbly at a real model without any SDK dependency: wrap ANY
`call(input)->output` with response caching + a hard call cap.

Caching makes the baseline runs (same input, repeated) cost exactly one call,
and the cap bounds spend. Bring your own provider — e.g.
`cached_system(lambda prompt: anthropic_client(...).text, max_calls=200)`.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


def cached_system(
    call: Callable[[Any], Any],
    key: Optional[Callable[[Any], Any]] = None,
    max_calls: Optional[int] = None,
) -> Callable[[Any], Any]:
    """Return a cached wrapper around `call`.

    - `key(input) -> hashable` picks the cache key (default: `repr(input)`).
    - `max_calls` caps the number of *distinct* (cache-miss) calls; exceeding it
      raises RuntimeError. `None` means unbounded.

    The wrapper exposes `.cache` (dict) and `.calls()` (distinct-call count).
    """
    cache: dict = {}
    made = {"n": 0}
    keyfn = key or (lambda x: repr(x))

    def wrapped(x: Any) -> Any:
        k = keyfn(x)
        if k in cache:
            return cache[k]
        if max_calls is not None and made["n"] >= max_calls:
            raise RuntimeError(f"cached_system exceeded max_calls={max_calls}")
        made["n"] += 1
        out = call(x)
        cache[k] = out
        return out

    wrapped.cache = cache
    wrapped.calls = lambda: made["n"]
    return wrapped
