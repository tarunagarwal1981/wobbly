"""wobbly — metamorphic testing for AI outputs. No answer key required."""

__version__ = "0.6.0"

from .core import check, Relation, Report, Counterexample
from .batch import check_batch, BatchReport, AuditResult
from .assertions import consistent_pick, equivalent
from .order import order_invariant, permute, position_sweep, slide
from .judge import judge_bias, JudgeBiasResult, length_bias, LengthBiasResult
from .text import (distractor_robust, formatting_invariant, paraphrase_invariant,
                   length_invariant, pad_text)
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
    "check_batch",
    "BatchReport",
    "AuditResult",
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
    "position_sweep",
    "slide",
    "judge_bias",
    "JudgeBiasResult",
    "length_bias",
    "LengthBiasResult",
    "distractor_robust",
    "formatting_invariant",
    "paraphrase_invariant",
    "length_invariant",
    "pad_text",
    # delivery
    "assert_robust",
    "cached_system",
    "extract_total",
]
