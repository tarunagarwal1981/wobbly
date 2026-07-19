"""wobbly — metamorphic testing for AI outputs. No answer key required."""

__version__ = "0.1.0"

from .core import check, Relation, Report, Counterexample
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
    "scales_by",
    "extract_total",
]
