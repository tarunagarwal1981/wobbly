"""Blind metamorphic run over real receipts, then ground-truth validation.

Stage 1 (BLIND): for each receipt, run invar with the extraction relation pack.
                 NO ground-truth label is read here. invar flags receipts where
                 the extractor contradicts itself under order/footer/currency
                 changes.

Stage 2 (AUDIT): only now do we open the labels, purely to measure whether the
                 blind flags actually correspond to wrong extractions.

The claim the article makes rests entirely on Stage 2 confirming Stage 1.

Cohorts: the extraction rules were developed against the first 120 receipts
(DEV). The remaining 415 (HELD-OUT) were never looked at while writing the
rules, so they are effectively test data — accuracy there is the honest
generalization number. We report DEV, HELD-OUT and COMBINED separately.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invar import check, default_pack, extract_total

# Receipts 0..DEV_N-1 are the ones the extractor/relation rules were iterated
# against. Everything after is held-out (never inspected during rule dev).
DEV_N = 120


def system(receipt: dict):
    return extract_total(receipt["lines"])


def stage1_blind(receipts):
    """Return the receipts invar flags — WITHOUT reading any label."""
    flagged = []
    for r in receipts:
        rep = check(system, r, default_pack(), samples=8, subject=r["id"])
        if rep.broke:
            flagged.append((r, rep))
    return flagged


def stage2_audit(receipts, flagged):
    """Open labels ONLY here, to score the blind flags."""
    def is_wrong(r):
        got = system(r)
        truth = float(r["true_total"])
        return got is None or abs(got - truth) > 0.011

    flagged_ids = {r["id"] for r, _ in flagged}
    not_flagged = [r for r in receipts if r["id"] not in flagged_ids]
    wrong_flagged = sum(1 for r, _ in flagged if is_wrong(r))
    wrong_not_flagged = sum(1 for r in not_flagged if is_wrong(r))
    total_wrong = wrong_flagged + wrong_not_flagged
    n = len(receipts)

    return {
        "n": n,
        "accuracy": (n - total_wrong) / n,
        "flagged": len(flagged),
        "wrong_flagged": wrong_flagged,
        "not_flagged": len(not_flagged),
        "wrong_not_flagged": wrong_not_flagged,
        "total_wrong": total_wrong,
        "precision": wrong_flagged / len(flagged) if flagged else 0.0,
        "err_flagged": wrong_flagged / len(flagged) if flagged else 0.0,
        "err_not_flagged": wrong_not_flagged / len(not_flagged) if not_flagged else 0.0,
    }


def report(label, receipts):
    flagged = stage1_blind(receipts)            # Stage 1 — no labels
    s = stage2_audit(receipts, flagged)         # Stage 2 — labels opened
    lift = (s["err_flagged"] / s["err_not_flagged"]) if s["err_not_flagged"] else float("inf")
    recall = s["wrong_flagged"] / s["total_wrong"] if s["total_wrong"] else 0.0
    print(f"-- {label}  (n={s['n']}) " + "-" * max(0, 40 - len(label)))
    print(f"   Stage 1 BLIND : flagged {s['flagged']}/{s['n']} "
          f"({100*s['flagged']/s['n']:.0f}%)   [no labels read]")
    print(f"   Stage 2 AUDIT : baseline accuracy {100*s['accuracy']:.0f}% "
          f"({s['n']-s['total_wrong']} right / {s['total_wrong']} wrong)")
    print(f"                   precision of flags {100*s['precision']:.0f}% "
          f"({s['wrong_flagged']}/{s['flagged']})")
    print(f"                   error rate flagged {100*s['err_flagged']:.0f}% "
          f"vs not-flagged {100*s['err_not_flagged']:.0f}%  => {lift:.1f}x more likely wrong")
    print(f"                   recall {100*recall:.0f}% "
          f"({s['wrong_flagged']}/{s['total_wrong']} of all errors) — high precision, low recall")
    print()
    return flagged


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    receipts = json.load(open(os.path.join(here, "..", "data", "receipts.json")))
    dev, held = receipts[:DEV_N], receipts[DEV_N:]

    print("=" * 64)
    print("TWO-STAGE BLIND + AUDIT over real ICDAR-SROIE receipts")
    print("Stage 1 reads NO ground truth. Stage 2 opens labels only to score.")
    print("=" * 64)
    report(f"DEV (first {DEV_N}, rules iterated here)", dev)
    report("HELD-OUT (rest, never seen in rule dev)", held)
    combined_flagged = report("COMBINED", receipts)
    print("=" * 64)

    # concrete catches for the article (blind — found with no answer key)
    print("\nConcrete catches (blind, from COMBINED):")
    shown = 0
    for r, rep in combined_flagged:
        got = system(r)
        c = rep.counterexamples[0]
        print(f"  receipt {r['id']}: extractor said {got} | truth {r['true_total']} | "
              f"{c.relation}: {c.before} -> {c.after}")
        shown += 1
        if shown == 5:
            break


if __name__ == "__main__":
    main()
