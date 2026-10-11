"""Minimal CLI. Subcommands:
  wobbly version          print the installed version
  wobbly demo             self-contained order-bias catch (no setup)
  wobbly judge [FILE]     measure position bias in an LLM judge, no labels

`wobbly judge myjudge.py` loads a `judge(case)` callable and a `cases` list from
your file and reports how often the verdict flips when the two answers swap —
the terminal front-end to wobbly.judge_bias. With no FILE it runs a demo."""
from __future__ import annotations

import argparse
from typing import List, Optional


def _demo() -> int:
    from .core import check
    from .order import order_invariant

    biased = lambda mcq: mcq["options"][0]          # leans to the first option
    mcq = {"options": ["Dolphin", "Shark", "Tuna", "Octopus"]}
    report = check(biased, mcq, [order_invariant(field="options")],
                   samples=20, baseline_runs=1, subject="demo")
    print("A model that always picks the first option is checked for order bias:")
    print(report.summary())
    if report.broke:
        c = report.counterexamples[0]
        print(f"  - reordering the options changed the pick: {c.before!r} -> {c.after!r}")
    print("No answer key was used.")
    return 0


# --- wobbly judge -----------------------------------------------------------

_DEMO_CASES = [
    {"question": "Which name is better for a focus app?", "answers": ["FocusFlow", "TaskNest"]},
    {"question": "Which tip is better?",
     "answers": ["Avoid screens before bed.", "Keep a consistent schedule."]},
    {"question": "Which commit message is clearer?",
     "answers": ["fix bug", "fix off-by-one error in pagination offset"]},
]


def _load_user_judge(path: str):
    """Import FILE and return (judge, cases). FILE must define a callable
    `judge(case)` and a non-empty list `cases`."""
    import importlib.util
    import os

    if not os.path.isfile(path):
        raise SystemExit(f"wobbly judge: file not found: {path}")
    spec = importlib.util.spec_from_file_location("_wobbly_user_judge", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"wobbly judge: could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:  # surface the user's own import error clearly
        raise SystemExit(f"wobbly judge: error importing {path}: {e!r}")

    judge = getattr(mod, "judge", None)
    cases = getattr(mod, "cases", None)
    if not callable(judge):
        raise SystemExit(f"wobbly judge: {path} must define a callable `judge(case)`.")
    if not cases:
        raise SystemExit(f"wobbly judge: {path} must define a non-empty list `cases`.")
    return judge, cases


def _judge_cmd(path: Optional[str], samples: int, baseline: int, fail_on_flip: bool) -> int:
    from .judge import judge_bias

    if path is None:
        print("DEMO: a judge that always prefers whichever answer is listed first.\n")
        judge = lambda case: "A"
        cases = _DEMO_CASES
    else:
        judge, cases = _load_user_judge(path)

    res = judge_bias(judge, cases, samples=samples, baseline_runs=baseline)
    print(res.summary())
    print("\nNo answer key used — this measures self-consistency under answer swap only.")
    if fail_on_flip and res.flipped:
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wobbly", description="metamorphic testing for AI outputs — no answer key")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("version", help="print the installed version")
    sub.add_parser("demo", help="run a self-contained order-bias catch")

    jp = sub.add_parser("judge", help="measure position bias in an LLM judge (no labels)")
    jp.add_argument("file", nargs="?",
                    help="Python file defining judge(case) and cases=[...]; omit for a demo")
    jp.add_argument("--samples", type=int, default=8, help="orderings tried per case (default 8)")
    jp.add_argument("--baseline", type=int, default=4,
                    help="unswapped runs used to measure the judge's own noise (default 4)")
    jp.add_argument("--fail-on-flip", action="store_true",
                    help="exit non-zero if any pair flips (for CI gating)")

    args = parser.parse_args(argv)

    if args.cmd == "version":
        from . import __version__
        print(__version__)
        return 0
    if args.cmd == "demo":
        return _demo()
    if args.cmd == "judge":
        return _judge_cmd(args.file, args.samples, args.baseline, args.fail_on_flip)
    parser.print_help()
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
