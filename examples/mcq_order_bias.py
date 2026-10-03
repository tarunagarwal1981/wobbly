"""Catch option-order bias in a multiple-choice system — with no answer key.

A toy 'LLM' that (like many real ones) is biased toward the FIRST option. wobbly
shuffles the options — which must not change a correct answer — and flags that the
pick moves. No correct answer is ever supplied.

Run:  python examples/mcq_order_bias.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wobbly import check, order_invariant


def biased_model(mcq):
    """Stand-in for an order-biased classifier: leans toward the first option."""
    return mcq["options"][0]


def main():
    mcq = {
        "question": "Which animal is a mammal?",
        "options": ["Dolphin", "Shark", "Tuna", "Octopus"],
    }

    rel = order_invariant(field="options")
    report = check(biased_model, mcq, [rel], samples=20, baseline_runs=1, subject="mcq")

    print("question:", mcq["question"])
    print("options  :", mcq["options"])
    print("model pick:", biased_model(mcq))
    print()
    print(report.summary())
    if report.broke:
        c = report.counterexamples[0]
        print(f"  - shuffling the options changed the pick: {c.before!r} -> {c.after!r}")
    print()
    print("No correct answer was ever supplied. wobbly used only the fact that")
    print("a correct answer cannot depend on the order the options are listed in.")


if __name__ == "__main__":
    main()
