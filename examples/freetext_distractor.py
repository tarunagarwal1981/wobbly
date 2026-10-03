"""Free-text robustness with an INJECTED embedder — exercising the baseline-variance
control honestly.

The toy summarizer PARAPHRASES ITSELF run-to-run (the model's own variance), and
also has a bug: an irrelevant sentence about pizza derails it. wobbly measures the
summarizer's own paraphrase spread on the clean doc first, then flags the
distractor only because it moves the meaning FURTHER than that spread. No answer key.

The embedder here is a tiny bag-of-words stand-in for the demo; in real use inject
your own (a sentence-transformer, or a provider's embedding API). wobbly bundles none.

Run:  python examples/freetext_distractor.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wobbly import check, distractor_robust, equivalent


def toy_embed(text):
    vocab = ["refund", "approved", "review", "weather", "pizza", "lunch"]
    t = text.lower()
    return [float(t.count(w)) for w in vocab]


_rng = random.Random(0)


def noisy_summarizer(doc):
    # Paraphrases itself run-to-run (intrinsic variance), but an irrelevant
    # mention of pizza wrongly changes the meaning.
    if "pizza" in doc.lower():
        return "The customer wants pizza for lunch."
    return _rng.choice([
        "The refund was approved.",
        "Refund approved after review.",
        "Approved the refund on review.",
    ])


def main():
    doc = "The customer's refund was approved after review."
    rel = distractor_robust(
        distractor="Unrelated: I had pizza for lunch.",
        assertion=equivalent(toy_embed),
    )
    report = check(noisy_summarizer, doc, [rel], baseline_runs=4, subject="summary")

    print("doc      :", doc)
    print("baseline :", report.baseline, "  <- the model's own paraphrase spread")
    print()
    print(report.summary())
    if report.broke:
        c = report.counterexamples[0]
        print(f"  - the irrelevant sentence moved the meaning beyond that spread:")
        print(f"    {c.before!r} -> {c.after!r}")
    print()
    print("No reference summary was used — only that irrelevant text must not change")
    print("the meaning by more than the model already varies on its own.")


if __name__ == "__main__":
    main()
