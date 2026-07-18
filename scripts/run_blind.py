"""Blind metamorphic run over real receipts, then ground-truth validation.

Stage 1 (BLIND): for each receipt, run invar with the extraction relation pack.
                 NO ground-truth label is read here. invar flags receipts where
                 the extractor contradicts itself under order/footer/currency
                 changes.

Stage 2 (AUDIT): only now do we open the labels, purely to measure whether the
                 blind flags actually correspond to wrong extractions.

The claim the article makes rests entirely on Stage 2 confirming Stage 1.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from invar import check, default_pack, extract_total


def system(receipt: dict):
    return extract_total(receipt["lines"])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    receipts = json.load(open(os.path.join(here, "..", "data", "receipts.json")))

    flagged = []          # receipts invar flagged, BLIND
    for r in receipts:
        rep = check(system, r, default_pack(), samples=8, subject=r["id"])
        if rep.broke:
            flagged.append((r, rep))

    # ---------- Stage 1 result (no labels used) ----------
    print("=" * 64)
    print(f"STAGE 1 — BLIND (no ground truth read)")
    print(f"  receipts tested : {len(receipts)}")
    print(f"  invar flagged   : {len(flagged)}  "
          f"({100*len(flagged)/len(receipts):.0f}% self-contradicted)")
    print("=" * 64)

    # ---------- Stage 2: audit flags against the held-out labels ----------
    def is_wrong(r):
        got = system(r)
        truth = float(r["true_total"])
        return got is None or abs(got - truth) > 0.011

    flagged_ids = {r["id"] for r, _ in flagged}
    wrong_and_flagged = sum(1 for r, _ in flagged if is_wrong(r))
    not_flagged = [r for r in receipts if r["id"] not in flagged_ids]
    wrong_and_not_flagged = sum(1 for r in not_flagged if is_wrong(r))

    total_wrong = wrong_and_flagged + wrong_and_not_flagged
    precision = wrong_and_flagged / len(flagged) if flagged else 0.0
    error_rate_flagged = wrong_and_flagged / len(flagged) if flagged else 0.0
    error_rate_clean = wrong_and_not_flagged / len(not_flagged) if not_flagged else 0.0

    print(f"STAGE 2 — AUDIT (labels opened only to score the blind flags)")
    print(f"  extractor errors total        : {total_wrong} / {len(receipts)}")
    print(f"  of invar's {len(flagged)} flags, actually wrong : {wrong_and_flagged}"
          f"  (precision {precision:.0%})")
    print(f"  error rate among FLAGGED       : {error_rate_flagged:.0%}")
    print(f"  error rate among NOT-flagged   : {error_rate_clean:.0%}")
    if error_rate_clean > 0:
        print(f"  => flagged receipts are {error_rate_flagged/error_rate_clean:.1f}x "
              f"more likely to be wrong")
    print("=" * 64)

    # show three concrete catches for the article
    print("\nThree concrete catches (blind):")
    shown = 0
    for r, rep in flagged:
        got = system(r)
        truth = r["true_total"]
        c = rep.counterexamples[0]
        print(f"  receipt {r['id']}: extractor said {got} | truth {truth} | "
              f"{c.relation}: {c.before} -> {c.after}")
        shown += 1
        if shown == 3:
            break


if __name__ == "__main__":
    main()
