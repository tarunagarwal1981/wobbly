"""Run wobbly over a whole dataset, not one input.

`check_batch` applies `check` to each input and aggregates the flags — the BLIND
stage, labels never touched. Scoring those flags against ground truth is a
separate, explicit `BatchReport.audit(is_error)` call (the AUDIT stage), so the
two-stage separation that makes the result trustworthy stays visible in the API.

This is offline / CI / sampling work: run it over a batch or a sample of
production traffic, not as a wrapper on every live request.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

from .core import check, Relation, Report, _jsonable


@dataclass
class _Entry:
    index: int
    input: Any
    output: Any            # system's output on the un-perturbed input (baseline[0])
    broke: bool
    rate: float            # strongest per-relation violation rate for this input
    errored: bool
    report: Optional[Report] = None   # kept only for flagged inputs


@dataclass
class AuditResult:
    n_flagged: int
    n_notflagged: int
    flagged_errors: int
    notflagged_errors: int
    precision: Optional[float]            # errors among flagged / flagged
    notflagged_error_rate: Optional[float]
    enrichment: Optional[float]           # precision / notflagged_error_rate

    def summary(self) -> str:
        p = "n/a" if self.precision is None else f"{100*self.precision:.0f}%"
        nf = "n/a" if self.notflagged_error_rate is None else f"{100*self.notflagged_error_rate:.0f}%"
        if self.enrichment is None:
            enr = "n/a"
        elif self.enrichment == float("inf"):
            enr = "inf (no errors among non-flagged)"
        else:
            enr = f"{self.enrichment:.1f}x"
        return (f"AUDIT: flagged error rate {p} ({self.flagged_errors}/{self.n_flagged}) "
                f"vs not-flagged {nf} ({self.notflagged_errors}/{self.n_notflagged}) "
                f"=> {enr} enriched for errors")

    def to_dict(self) -> dict:
        return {
            "n_flagged": self.n_flagged, "n_notflagged": self.n_notflagged,
            "flagged_errors": self.flagged_errors, "notflagged_errors": self.notflagged_errors,
            "precision": self.precision, "notflagged_error_rate": self.notflagged_error_rate,
            "enrichment": (None if self.enrichment is None
                           else ("inf" if self.enrichment == float("inf") else self.enrichment)),
        }


@dataclass
class BatchReport:
    n: int = 0
    entries: List[_Entry] = field(default_factory=list)

    @property
    def flagged(self) -> List[int]:
        return [e.index for e in self.entries if e.broke]

    @property
    def errored(self) -> List[int]:
        return [e.index for e in self.entries if e.errored]

    @property
    def flag_rate(self) -> float:
        return len(self.flagged) / self.n if self.n else 0.0

    def summary(self) -> str:
        head = f"flagged {len(self.flagged)}/{self.n} ({100*self.flag_rate:.1f}%)"
        if self.errored:
            head += f"; {len(self.errored)} errored"
        return head + "  (no answer key used)"

    def to_dict(self, include_reports: bool = False) -> dict:
        d: Dict[str, Any] = {
            "n": self.n,
            "flagged": self.flagged,
            "flag_rate": self.flag_rate,
            "errored": self.errored,
            "per_input": [
                {"index": e.index, "broke": e.broke, "rate": e.rate, "output": _jsonable(e.output)}
                for e in self.entries
            ],
        }
        if include_reports:
            d["reports"] = {e.index: e.report.to_dict() for e in self.entries if e.report is not None}
        return d

    def audit(self, is_error: Callable[[Any, Any], bool]) -> AuditResult:
        """AUDIT stage (opens labels). `is_error(input, output) -> bool` says
        whether the system's output on that input was actually wrong. Compares the
        error rate among flagged vs non-flagged inputs. Errored inputs are excluded
        from both groups (no valid output to score)."""
        flagged = [e for e in self.entries if e.broke]
        notflagged = [e for e in self.entries if not e.broke and not e.errored]
        fe = sum(1 for e in flagged if is_error(e.input, e.output))
        ne = sum(1 for e in notflagged if is_error(e.input, e.output))
        precision = fe / len(flagged) if flagged else None
        nf_rate = ne / len(notflagged) if notflagged else None
        if precision is None or nf_rate is None:
            enrichment = None
        elif nf_rate == 0:
            enrichment = float("inf") if precision > 0 else None
        else:
            enrichment = precision / nf_rate
        return AuditResult(n_flagged=len(flagged), n_notflagged=len(notflagged),
                           flagged_errors=fe, notflagged_errors=ne,
                           precision=precision, notflagged_error_rate=nf_rate,
                           enrichment=enrichment)


def check_batch(
    system: Callable[[Any], Any],
    inputs: Iterable[Any],
    relations: List[Relation],
    samples: int = 20,
    baseline_runs: int = 5,
) -> BatchReport:
    """Run `check` on every input and aggregate the flags (BLIND — no labels).

    Identical per-input behaviour to calling `check` yourself in a loop; this just
    collects the results. Score the flags afterwards with `BatchReport.audit`."""
    report = BatchReport()
    for i, inp in enumerate(inputs):
        rep = check(system, inp, relations, samples=samples,
                    baseline_runs=baseline_runs, subject=f"input[{i}]")
        rate = max((s.rate for s in rep.relation_stats), default=0.0)
        report.entries.append(_Entry(
            index=i, input=inp,
            output=rep.baseline[0] if rep.baseline else None,
            broke=rep.broke, rate=rate, errored=bool(rep.errors),
            report=rep if rep.broke else None,
        ))
    report.n = len(report.entries)
    return report
