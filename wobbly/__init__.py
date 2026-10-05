"""wobbly — metamorphic testing for AI outputs. No answer key required."""

__version__ = "0.2.0"

from .core import check, Relation, Report, Counterexample
from .assertions import consistent_pick, equivalent
from .order import order_invariant, permute
from .judge import judge_bias, JudgeBiasResult
from .text import distractor_robust, formatting_invariant, paraphrase_invariant
from .testing import assert_robust
from .llm import cached_system
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
    "equivalent",
    # general relations
    "order_invariant",
    "permute",
    "judge_bias",
    "JudgeBiasResult",
    "distractor_robust",
    "formatting_invariant",
    "paraphrase_invariant",
    # delivery
    "assert_robust",
    "cached_system",
    "extract_total",
]
