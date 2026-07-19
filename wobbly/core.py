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
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


# A transform mutates an input in a way whose effect on the output is known.
Transform = Callable[[Any], Any]
# An assertion decides whether (output_before, output_after) is consistent.
Assertion = Callable[[Any, Any], bool]


@dataclass(frozen=True)
class Relation:
    """A metamorphic relation: transform the input, assert on the two outputs.

    INPUT CONTRACT: `transform` receives the same `base_input` you pass to
    `check`, and must return a value of that same shape — because `check` feeds
    the transformed value straight back into your `system`. So `base_input`,
    `system`, and every `transform` must agree on one input type. The built-in
    pack operates on a receipt dict `{"lines": [...]}`, so a `lines -> total`
    extractor is adapted with `lambda r: extract_total(r["lines"])`.

    Set `deterministic=True` if the transform always produces the same output for
    a given input (e.g. appending a fixed footer). `check` then runs it once
    instead of `samples` times — no coverage is lost, and if `system` is a paid
    API call this avoids paying for identical repeats. Leave it False for
    randomized transforms (e.g. a shuffle), which need multiple samples.
    """
    name: str
    transform: Transform
    assertion: Assertion
    deterministic: bool = False


@dataclass(frozen=True)
class Counterexample:
    relation: str
    before: Any
    after: Any
    detail: str = ""


@dataclass
class Report:
    subject: str = ""
    counterexamples: List[Counterexample] = field(default_factory=list)
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
            return f"{head}OK — {self.trials} trials, no contradiction found"
        lines = [f"{head}BROKE ({len(self.counterexamples)} of {self.trials} trials):"]
        for c in self.counterexamples[:5]:
            lines.append(f"  [{c.relation}] {c.detail}")
        if len(self.counterexamples) > 5:
            lines.append(f"  ... and {len(self.counterexamples) - 5} more")
        return "\n".join(lines)


def check(
    system: Callable[[Any], Any],
    base_input: Any,
    relations: List[Relation],
    samples: int = 20,
    subject: str = "",
) -> Report:
    """Run `system` against each relation up to `samples` times.

    `system` is your AI/extractor: input -> output. wobbly never learns the
    "right" output; it only checks the relations you assert.

    `samples` applies to randomized relations; a relation marked
    `deterministic=True` is run once regardless (see `Relation`). All of
    `base_input`, `system`, and each relation's transform must accept the same
    input shape.
    """
    report = Report(subject=subject)
    try:
        base_output = system(base_input)
    except Exception as e:  # a system that crashes on the base input is its own bug
        report.errors.append(f"system raised on base input: {e!r}")
        return report

    for rel in relations:
        n = 1 if rel.deterministic else samples
        for _ in range(n):
            report.trials += 1
            try:
                mutated = rel.transform(base_input)
                mutated_output = system(mutated)
            except Exception as e:
                report.errors.append(f"{rel.name}: transform/system raised: {e!r}")
                break
            if not rel.assertion(base_output, mutated_output):
                report.counterexamples.append(
                    Counterexample(
                        relation=rel.name,
                        before=base_output,
                        after=mutated_output,
                        detail=f"expected {base_output!r} to be preserved, got {mutated_output!r}",
                    )
                )
                break  # one counterexample per relation is enough to prove the break
    return report
