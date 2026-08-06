"""
wobbly works on ANY `input -> output` system — not just receipts.

Here the system under test is a tiny sentiment classifier (`str -> label`).
No receipts, no line-lists: a string goes in, a label comes out. We use the
*same* engine as the receipt demo — `check` + `Relation` + `unchanged`.

The classifier below has a realistic bug: it's case-sensitive, so it only
recognises lowercase cue words. A transformation that *shouldn't* matter —
changing the letter case — exposes it, with no labelled data.

Run:  python examples/classifier_example.py
"""

from wobbly import check, Relation, unchanged

POSITIVE = {"love", "great", "excellent", "amazing", "good"}
NEGATIVE = {"hate", "terrible", "awful", "bad", "broken"}


def classify_sentiment(text: str) -> str:
    """System under test: text -> 'positive' | 'negative' | 'neutral'.

    The bug: it never lowercases the text, so 'LOVE' is invisible to it.
    """
    words = [w.strip(".,!?") for w in text.split()]  # note: no .lower() -> the bug
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


# Two metamorphic relations for a NON-receipt task — each is a change whose
# effect on the correct answer is known (it shouldn't change), so a *correct*
# classifier passes and only a real defect fails.

casing = Relation(
    name="changing letter case shouldn't change the sentiment",
    transform=lambda text: text.upper(),
    assertion=unchanged(),
    deterministic=True,  # .upper() is fixed for a given input -> run once
)

neutral_noise = Relation(
    name="adding a neutral sentence shouldn't change the sentiment",
    transform=lambda text: text + " The store opens at nine.",
    assertion=unchanged(),
    deterministic=True,
)


def main():
    review = "I love this product"
    print(f"input : {review!r}")
    print(f"output: {classify_sentiment(review)!r}\n")

    report = check(classify_sentiment, review, [casing, neutral_noise])
    print(report.summary())
    for c in report.counterexamples:
        print(f"  - [{c.relation}] {c.before!r} -> {c.after!r}")

    print(
        "\nNo correct label was ever supplied. wobbly only used the fact that "
        "case shouldn't flip a sentiment — and caught the case-sensitivity bug."
    )


if __name__ == "__main__":
    main()
