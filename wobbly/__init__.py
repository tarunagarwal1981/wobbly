"""wobbly — metamorphic testing for AI outputs. No answer key required."""

__version__ = "0.1.1"

from .core import check, Relation, Report, Counterexample
from .assertions import consistent_pick
from .order import order_invariant, permute
from .relations import (
    default_pack,
    total_reorder_invariant,
    total_footer_invariant,
    total_currency_invariant,
    reorder_lines,
    inject_footer,
    normalize_currency,
    unchanged,
    scales_by,
)
from .extractor import extract_total

__all__ = [
    "__version__",
    "check",
    "Relation",
    "Report",
    "Counterexample",
    "default_pack",
    "total_reorder_invariant",
    "total_footer_invariant",
    "total_currency_invariant",
    # transforms — building blocks for composing your own relations
    "reorder_lines",
    "inject_footer",
    "normalize_currency",
    "unchanged",
    "consistent_pick",
    "scales_by",
    # general relations
    "order_invariant",
    "permute",
    "extract_total",
]
