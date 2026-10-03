from wobbly import check
from wobbly.order import order_invariant, permute


def test_flags_option_order_bias_field_shaper():
    first = lambda mcq: mcq["options"][0]
    rel = order_invariant(field="options")
    mcq = {"q": "pick one", "options": ["A", "B", "C", "D"]}
    rep = check(first, mcq, [rel], samples=20, baseline_runs=1)
    assert rep.broke is True


def test_passes_order_robust_system():
    rel = order_invariant(field="options")
    mcq = {"q": "pick one", "options": ["A", "B", "C", "D"]}
    rep = check(lambda m: "B", mcq, [rel], samples=20, baseline_runs=1)
    assert rep.broke is False


def test_plain_list_shaper():
    rel = order_invariant()
    rep = check(lambda xs: xs[0], ["A", "B", "C"], [rel], samples=10, baseline_runs=1)
    assert rep.broke is True


def test_accessor_shaper_preserves_other_parts():
    seen = {}
    def sys(t):
        seen["query"] = t[0]
        return t[1][0]
    rel = order_invariant(get=lambda t: t[1], set=lambda t, v: (t[0], v))
    rep = check(sys, ("my-query", ["d1", "d2", "d3"]), [rel], samples=10, baseline_runs=1)
    assert rep.broke is True
    assert seen["query"] == "my-query"


def test_abstains_on_fewer_than_two_elements():
    rel = order_invariant(field="options")
    mcq = {"q": "x", "options": ["only"]}
    rep = check(lambda m: m["options"][0], mcq, [rel], samples=5, baseline_runs=1)
    assert rep.broke is False


def test_permute_is_reproducible():
    t1 = permute(lambda x: x, lambda x, v: v)
    t2 = permute(lambda x: x, lambda x, v: v)
    base = ["a", "b", "c", "d"]
    assert [t1(base) for _ in range(6)] == [t2(base) for _ in range(6)]


def test_requires_both_get_and_set_or_neither():
    import pytest
    with pytest.raises(ValueError):
        order_invariant(get=lambda x: x)
