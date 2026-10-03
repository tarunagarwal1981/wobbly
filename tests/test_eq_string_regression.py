"""Regression: numeric-looking STRINGS must not be coerced to equal. A string/label
output that genuinely changes under a perturbation must be flagged."""
from wobbly.assertions import unchanged, consistent_pick


def test_numeric_looking_strings_are_not_coerced():
    u = unchanged()
    assert u.consistent(["1.10"], "1.1") is False      # different strings -> flagged
    assert u.consistent(["007"], "7") is False
    assert u.consistent(["1e3"], "1000") is False
    assert u.consistent(["5.0"], "5.0") is True        # identical string -> consistent


def test_consistent_pick_strings_exact():
    cp = consistent_pick()
    assert cp.consistent(["1.10", "1.100"], "1.1") is False
    assert cp.consistent(["1.10", "1.1"], "1.1") is True


def test_real_numbers_still_tolerant():
    u = unchanged()
    assert u.consistent([5.0, 5.0], 5.0) is True
    assert u.consistent([5.0], 5.0 + 1e-9) is True      # within tolerance
    assert u.consistent([5.0], 6.0) is False
