"""check_batch (BLIND dataset run) + BatchReport.audit (AUDIT) + to_dict."""
import json

from wobbly import check, check_batch, order_invariant

MCQS = [{"options": ["A", "B", "C"]}, {"options": ["X", "Y", "Z"]}]


def test_check_batch_flags_biased_system():
    first = lambda m: m["options"][0]
    rep = check_batch(first, MCQS, [order_invariant(field="options")], samples=10, baseline_runs=1)
    assert rep.n == 2
    assert rep.flagged == [0, 1]
    assert rep.flag_rate == 1.0


def test_check_batch_robust_system():
    rep = check_batch(lambda m: "B", MCQS, [order_invariant(field="options")], samples=10, baseline_runs=1)
    assert rep.flagged == []
    assert rep.flag_rate == 0.0


def test_audit_enrichment_math():
    inputs = [
        {"options": ["a", "b", "c"], "biased": True, "err": True},    # 0 flagged, error
        {"options": ["a", "b", "c"], "biased": True, "err": False},   # 1 flagged, ok
        {"options": ["a", "b", "c"], "biased": False, "err": True},   # 2 not-flagged, error
        {"options": ["a", "b", "c"], "biased": False, "err": False},  # 3 not-flagged, ok
    ]
    system = lambda m: m["options"][0] if m["biased"] else "FIXED"
    rep = check_batch(system, inputs, [order_invariant(field="options")], samples=10, baseline_runs=1)
    assert rep.flagged == [0, 1]
    audit = rep.audit(lambda inp, out: inp["err"])
    assert audit.precision == 0.5                 # 1 of 2 flagged were errors
    assert audit.notflagged_error_rate == 0.5     # 1 of 2 not-flagged were errors
    assert audit.enrichment == 1.0
    assert "enriched" in audit.summary()


def test_audit_divide_by_zero_guarded():
    first = lambda m: m["options"][0]
    rep = check_batch(first, MCQS, [order_invariant(field="options")], samples=10, baseline_runs=1)
    # everything flagged -> no non-flagged group -> enrichment undefined, not a crash
    audit = rep.audit(lambda inp, out: True)
    assert audit.notflagged_error_rate is None
    assert audit.enrichment is None


def test_errored_input_excluded_from_flags():
    def system(m):
        if m.get("boom"):
            raise ValueError("kaboom")
        return m["options"][0]

    inputs = [{"options": ["a", "b"]}, {"options": ["a", "b"], "boom": True}]
    rep = check_batch(system, inputs, [order_invariant(field="options")], samples=6, baseline_runs=1)
    assert rep.errored == [1]
    assert rep.flagged == [0]


def test_batch_to_dict_json_serializable():
    first = lambda m: m["options"][0]
    rep = check_batch(first, MCQS, [order_invariant(field="options")], samples=6, baseline_runs=1)
    d = rep.to_dict()
    json.dumps(d)                                  # must not raise
    assert d["n"] == 2 and d["flagged"] == [0, 1] and len(d["per_input"]) == 2


def test_report_to_dict_json_serializable_with_exotic_output():
    # a system whose output is a non-JSON object (a set) -> repr fallback, no crash
    rep = check(lambda m: {frozenset(m["options"])}, {"options": ["a", "b"]},
                [order_invariant(field="options")], samples=4, baseline_runs=1)
    d = rep.to_dict()
    json.dumps(d)
    assert "broke" in d and "relation_stats" in d
