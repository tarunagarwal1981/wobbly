"""Drop wobbly into pytest/CI: `assert_robust(...)` runs a check and raises
AssertionError (with the report summary) when a relation is violated."""
from __future__ import annotations

from typing import Any, Callable, List

from .core import check, Relation, Report


def assert_robust(
    system: Callable[[Any], Any],
    base_input: Any,
    relations: List[Relation],
    samples: int = 20,
    baseline_runs: int = 5,
    subject: str = "",
) -> Report:
    """Run `check`; raise AssertionError if any relation is violated (or the
    system errored). Returns the Report on success so callers can inspect it."""
    report = check(system, base_input, relations,
                   samples=samples, baseline_runs=baseline_runs, subject=subject)
    if report.errors:
        raise AssertionError(report.errors[0])
    if report.broke:
        raise AssertionError(report.summary())
    return report
