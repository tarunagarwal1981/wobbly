"""wobbly — metamorphic testing for AI outputs. No answer key required.

The idea: you often cannot check an AI output against a "correct" answer,
because you don't have one. But you almost always know things that must stay
true when the INPUT changes in a known way:

    reorder an invoice's lines   -> the total must not move
    add an irrelevant sentence   -> the risk score must not change
    double every quantity        -> the total must double

`wobbly` takes your system (input -> output), a base input, and a list of such
relations. For each relation it transforms the input, runs the system on both,
and checks that the asserted relationship between the two outputs holds. When it
doesn't, you've found a bug — without ever knowing the right answer.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, List

from .assertions import Assertion

Transform = Callable[[Any], Any]


@dataclass(frozen=True)
class Relation:
    """A metamorphic relation: transform the input, then judge the output against
    the system's baseline via `assertion`.

    INPUT CONTRACT: `transform` receives the same `base_input` you pass to
    `check` and returns a value of that same shape, because `check` feeds it back
    into `system`. So base_input, system, and every transform share one input
    type.

    Set `deterministic=True` for a transform that always yields the same output
    for a given input (a fixed footer, a currency strip): `check` runs it once
    instead of `samples` times.
    """
    name: str
    transform: Transform
    assertion: Assertion
    deterministic: bool = False


@dataclass(frozen=True)
class Counterexample:
    relation: str
    before: Any            # a representative baseline output (baseline[0])
    after: Any
    detail: str = ""


@dataclass
class RelationStat:
    name: str
    trials: int = 0
    violations: int = 0

    @property
    def rate(self) -> float:
        return self.violations / self.trials if self.trials else 0.0


@dataclass
class Report:
    subject: str = ""
    baseline: List[Any] = field(default_factory=list)
    counterexamples: List[Counterexample] = field(default_factory=list)
    relation_stats: List[RelationStat] = field(default_factory=list)
    trials: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def broke(self) -> bool:
        return len(self.counterexamples) > 0

    def summary(self) -> str:
        head = f"[{self.subject}] " if self.subject else ""
        if self.errors:
            return f"{head}ERROR after {self.trials} trials: {self.errors[0]}"
        if not self.broke:
            return f"{head}OK — {self.trials} trials, no contradiction beyond baseline noise"
        lines = [f"{head}BROKE ({len(self.counterexamples)} relation(s) violated):"]
        for s in self.relation_stats:
            if s.violations:
                lines.append(f"  [{s.name}] violated {s.violations}/{s.trials} samples ({100*s.rate:.0f}%)")
        return "\n".join(lines)


def check(
    system: Callable[[Any], Any],
    base_input: Any,
    relations: List[Relation],
    samples: int = 20,
    baseline_runs: int = 5,
    subject: str = "",
) -> Report:
    """Run `system` against each relation, judging perturbed outputs against the
    system's own baseline so intrinsic run-to-run noise is not mistaken for a bug.

    `samples` applies to randomized relations; a `deterministic=True` relation is
    run once. `baseline_runs` is how many times the system is run on the
    un-perturbed input to measure its intrinsic output spread.
    """
    report = Report(subject=subject)
    try:
        baseline = [system(base_input) for _ in range(max(1, baseline_runs))]
    except Exception as e:  # a system that crashes on the base input is its own bug
        report.errors.append(f"system raised on base input: {e!r}")
        return report
    report.baseline = baseline
    ref = baseline[0]

    for rel in relations:
        n = 1 if rel.deterministic else samples
        stat = RelationStat(name=rel.name)
        first_ce = None
        for _ in range(n):
            report.trials += 1
            stat.trials += 1
            try:
                mutated = rel.transform(base_input)
                after = system(mutated)
            except Exception as e:
                report.errors.append(f"{rel.name}: transform/system raised: {e!r}")
                break
            if not rel.assertion.consistent(baseline, after):
                stat.violations += 1
                if first_ce is None:
                    first_ce = Counterexample(
                        relation=rel.name,
                        before=ref,
                        after=after,
                        detail=f"expected {ref!r} to be preserved, got {after!r}",
                    )
        report.relation_stats.append(stat)
        if first_ce is not None:
            report.counterexamples.append(first_ce)
    return report
