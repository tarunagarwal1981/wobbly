import pytest
from wobbly import check, order_invariant
from wobbly.testing import assert_robust


def test_assert_robust_passes_for_robust_system():
    rep = assert_robust(lambda m: "B", {"options": ["A", "B", "C"]},
                        [order_invariant(field="options")], samples=10, baseline_runs=1)
    assert rep.broke is False


def test_assert_robust_raises_for_biased_system():
    with pytest.raises(AssertionError) as exc:
        assert_robust(lambda m: m["options"][0], {"options": ["A", "B", "C", "D"]},
                      [order_invariant(field="options")], samples=20, baseline_runs=1)
    assert "violated" in str(exc.value)
