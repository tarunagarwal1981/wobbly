from wobbly.assertions import Unchanged, ConsistentPick, ScalesBy, unchanged, consistent_pick, scales_by, Assertion


def test_unchanged_deterministic_baseline():
    a = unchanged()
    assert isinstance(a, Assertion)
    assert a.consistent([5.0, 5.0, 5.0], 5.0) is True
    assert a.consistent([5.0, 5.0, 5.0], 6.0) is False


def test_unchanged_none_safe():
    a = unchanged()
    assert a.consistent([None, None], None) is True
    assert a.consistent([None], 1.0) is False


def test_consistent_pick_allows_values_the_baseline_produced():
    a = consistent_pick()
    assert a.consistent(["A", "B", "A"], "A") is True
    assert a.consistent(["A", "B", "A"], "B") is True
    assert a.consistent(["A", "B", "A"], "C") is False


def test_scales_by():
    a = scales_by(2.0)
    assert a.consistent([10.0, 10.0], 20.0) is True
    assert a.consistent([10.0], 21.0) is False


def test_assertions_have_names():
    assert unchanged().name == "unchanged"
    assert consistent_pick().name == "consistent pick"
