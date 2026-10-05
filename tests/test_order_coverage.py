import pytest

from wobbly import check
from wobbly.order import order_invariant, permute, _rotations


def test_rotations_cover_each_position_once():
    rots = _rotations(4)
    assert len(rots) == 4
    for pos in range(4):
        assert sorted(r[pos] for r in rots) == [0, 1, 2, 3]


def test_rotate_is_deterministic():
    assert _rotations(5) == _rotations(5)


def test_default_is_random_and_unchanged():
    first = lambda mcq: mcq["options"][0]
    rel = order_invariant(field="options")      # no coverage arg
    mcq = {"options": ["A", "B", "C", "D"]}
    assert check(first, mcq, [rel], samples=20, baseline_runs=1).broke is True


def test_rotate_flags_first_option_bias():
    first = lambda mcq: mcq["options"][0]
    rel = order_invariant(field="options", coverage="rotate")
    mcq = {"options": ["A", "B", "C", "D"]}
    assert check(first, mcq, [rel], samples=10, baseline_runs=1).broke is True


def test_rotate_robust_system_passes():
    rel = order_invariant(field="options", coverage="rotate")
    mcq = {"options": ["A", "B", "C", "D"]}
    assert check(lambda m: "B", mcq, [rel], samples=10, baseline_runs=1).broke is False


def test_rotate_pairwise_is_both_orders():
    t = permute(lambda x: x, lambda b, e: e, coverage="rotate")
    seen = [tuple(t(["x", "y"])) for _ in range(2)]
    assert sorted(seen) == [("x", "y"), ("y", "x")]


def test_rotate_places_each_element_in_each_position():
    t = permute(lambda x: x, lambda b, e: e, coverage="rotate")
    outs = [t(["a", "b", "c"]) for _ in range(3)]
    for pos in range(3):
        assert sorted(o[pos] for o in outs) == ["a", "b", "c"]


def test_rotate_abstains_below_two_elements():
    t = permute(lambda x: x, lambda b, e: e, coverage="rotate")
    assert t(["only"]) == ["only"]


def test_unknown_coverage_rejected():
    with pytest.raises(ValueError):
        permute(lambda x: x, lambda b, e: e, coverage="zigzag")
    with pytest.raises(ValueError):
        order_invariant(field="options", coverage="zigzag")
