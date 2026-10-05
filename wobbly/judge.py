"""judge_bias — measure position bias in YOUR LLM judge, with no answer key.

Hand it a judge (any callable that picks between two answers) and some cases; it
swaps the answers' positions and reports how often the judge changes its mind.
It measures self-consistency only, never correctness — a judge that always picks
the better answer scores 0% regardless of which answer is "better".

The footgun this guards: swapping answers re-letters them, so a judge that
returns "A" means a different answer after the swap. judge_bias therefore
resolves whatever the judge returns — a letter OR the answer text — to the CHOSEN
CONTENT before comparing, so re-lettering is never counted as a flip.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, Iterable, List

from .core import check, Report
from .assertions import consistent_pick
from .order import order_invariant

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _resolve_pick(ret: Any, answers: List[Any]) -> Any:
    """Map a judge's return value to the chosen answer's content.

    Accepts the exact answer text, a letter ("A"/"b"/"B."), a response that
    contains exactly one answer's text, or a response with a standalone capital
    letter ("Answer: B"). Anything else falls back to str(ret)[:40]."""
    for a in answers:
        if ret == a:
            return a
    text = str(ret).strip()
    bare = text.strip(" .:)(\"'*").upper()
    if len(bare) == 1 and bare in _LETTERS[:len(answers)]:
        return answers[_LETTERS.index(bare)]
    contained = [a for a in answers if isinstance(a, str) and a and a in text]
    if len(contained) == 1:
        return contained[0]
    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Z])(?![A-Za-z0-9])", text):
        idx = _LETTERS.index(m.group(1))
        if idx < len(answers):
            return answers[idx]
    return text[:40]


@dataclass
class JudgeBiasResult:
    flip_rate: float                       # 0-1: swap trials where the pick changed
    flipped: int                           # cases with at least one flip
    n_cases: int
    per_case: List[Dict[str, Any]] = dc_field(default_factory=list)
    reports: List[Report] = dc_field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"judge position-bias: {self.flipped}/{self.n_cases} cases flipped "
            f"({100 * self.flip_rate:.0f}% of swap trials changed the pick)",
        ]
        for r in self.per_case:
            mark = "FLIP" if r["broke"] else "ok  "
            lines.append(f"  {mark} {r['flips']}/{r['trials']}  {r['question']}  "
                         f"(base pick: {r['base_pick']!r})")
        lines.append("Self-consistency under answer swap only; no answer key used.")
        return "\n".join(lines)


def judge_bias(
    judge: Callable[[Any], Any],
    cases: Iterable[Dict[str, Any]],
    field: str = "answers",
    samples: int = 8,
    baseline_runs: int = 4,
    return_reports: bool = False,
) -> JudgeBiasResult:
    """Measure how often `judge` changes its pick when the answers swap places.

    `judge(case)` receives the case (answers in the swapped order) and returns a
    letter ("A"/"B") or the chosen answer's text. `baseline_runs` re-runs the
    judge on the unswapped case so its own run-to-run noise is not counted.
    Uses coverage="rotate": at most min(samples, N) rotations per case (for a
    pair, exactly both orders)."""
    per_case: List[Dict[str, Any]] = []
    reports: List[Report] = []
    flipped = flips_total = trials_total = 0
    n = 0

    for case in cases:
        n += 1
        n_answers = len(case[field])

        def model_pick(c, _field=field):
            return _resolve_pick(judge(c), list(c[_field]))

        rel = order_invariant(field=field, assertion=consistent_pick(), coverage="rotate")
        rep = check(model_pick, case, [rel],
                    samples=max(1, min(samples, n_answers)),
                    baseline_runs=baseline_runs,
                    subject=str(case.get("question", "")))
        flips = sum(s.violations for s in rep.relation_stats)
        trials = sum(s.trials for s in rep.relation_stats)
        flips_total += flips
        trials_total += trials
        flipped += 1 if rep.broke else 0
        per_case.append({
            "question": case.get("question", ""),
            "base_pick": rep.baseline[0] if rep.baseline else None,
            "flips": flips,
            "trials": trials,
            "broke": rep.broke,
        })
        if return_reports:
            reports.append(rep)

    rate = flips_total / trials_total if trials_total else 0.0
    return JudgeBiasResult(flip_rate=rate, flipped=flipped, n_cases=n,
                           per_case=per_case, reports=reports)
