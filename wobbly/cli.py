"""Minimal CLI: `wobbly version` and a self-contained `wobbly demo` (an
order-bias catch that needs no external data, so it runs from a pip install).
Ad-hoc relation configuration lives in Python, not flags."""
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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wobbly", description="metamorphic testing for AI outputs — no answer key")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("version", help="print the installed version")
    sub.add_parser("demo", help="run a self-contained order-bias catch")
    args = parser.parse_args(argv)

    if args.cmd == "version":
        from . import __version__
        print(__version__)
        return 0
    if args.cmd == "demo":
        return _demo()
    parser.print_help()
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
