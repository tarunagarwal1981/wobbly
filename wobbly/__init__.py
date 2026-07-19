"""wobbly — metamorphic testing for AI outputs. No answer key required."""
from .core import check, Relation, Report, Counterexample
from .relations import (
    default_pack,
    total_reorder_invariant,
    total_footer_invariant,
    total_currency_invariant,
    unchanged,
    scales_by,
)
from .extractor import extract_total

__all__ = [
    "check",
    "Relation",
    "Report",
    "Counterexample",
    "default_pack",
    "total_reorder_invariant",
    "total_footer_invariant",
    "total_currency_invariant",
    "unchanged",
    "scales_by",
    "extract_total",
]
