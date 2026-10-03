from wobbly.assertions import equivalent, Equivalent, Assertion


VECS = {
    "the cat sat":       [1.0, 0.0],
    "a cat was sitting": [0.96, 0.28],
    "stock markets fell":[0.0, 1.0],
}
embed = lambda s: VECS[s]


def test_equivalent_is_an_assertion():
    assert isinstance(equivalent(embed), Assertion)


def test_within_baseline_spread_is_consistent():
    a = equivalent(embed)
    baseline = ["the cat sat", "a cat was sitting"]
    assert a.consistent(baseline, "a cat was sitting") is True


def test_beyond_baseline_spread_is_flagged():
    a = equivalent(embed)
    baseline = ["the cat sat", "a cat was sitting"]
    assert a.consistent(baseline, "stock markets fell") is False


def test_explicit_threshold():
    a = equivalent(embed, threshold=0.5)
    assert a.consistent(["the cat sat"], "stock markets fell") is False
    assert a.consistent(["the cat sat"], "the cat sat") is True
