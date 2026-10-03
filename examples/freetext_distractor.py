"""Free-text robustness with an INJECTED embedder (no bundled model).

A toy summarizer is distracted by an irrelevant sentence. We use a tiny
bag-of-words embedder just for the demo; in real use, inject your own
(a sentence-transformer, or a provider's embedding API). No answer key.

Run:  python examples/freetext_distractor.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wobbly import check, distractor_robust, equivalent


def toy_embed(text):
    # bag-of-words over a fixed vocab -> vector (DEMO ONLY; inject a real one)
    vocab = ["refund", "approved", "denied", "weather", "pizza", "order"]
    t = text.lower()
    return [float(t.count(w)) for w in vocab]


def distractible_summarizer(doc):
    # pathological: if the doc mentions pizza, it wrongly changes its summary
    if "pizza" in doc.lower():
        return "The customer wants a pizza."
    return "The refund was approved."


def main():
    doc = "The customer's refund was approved after review."
    rel = distractor_robust(
        distractor="Unrelated: I had pizza for lunch.",
        assertion=equivalent(toy_embed),
    )
    report = check(distractible_summarizer, doc, [rel], samples=3, baseline_runs=1,
                   subject="summary")
    print("doc    :", doc)
    print("summary:", distractible_summarizer(doc))
    print()
    print(report.summary())
    if report.broke:
        c = report.counterexamples[0]
        print(f"  - adding an irrelevant sentence changed the meaning: {c.before!r} -> {c.after!r}")
    print()
    print("No reference summary was used — only that irrelevant text must not")
    print("change the meaning, judged against the model's own baseline spread.")


if __name__ == "__main__":
    main()
