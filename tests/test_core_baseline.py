import itertools
from wobbly.core import check, Relation
from wobbly.assertions import unchanged, consistent_pick


def test_deterministic_system_flags_a_real_change():
    sys = lambda x: x[0]
    rel = Relation("swap first", transform=lambda x: x[::-1], assertion=unchanged())
    rep = check(sys, ["a", "b", "c"], [rel], samples=5, baseline_runs=3)
    assert rep.broke is True
    assert rep.baseline == ["a", "a", "a"]


def test_baseline_variance_suppresses_pure_noise():
    flip = itertools.cycle(["A", "B"])
    noisy = lambda x: next(flip)
    rel = Relation("noop", transform=lambda x: x, assertion=consistent_pick())
    rep = check(noisy, "anything", [rel], samples=10, baseline_runs=4)
    assert rep.broke is False


def test_violation_rate_is_counted_not_broken_on_first():
    import random
    rng = random.Random(0)
    sys = lambda x: x
    def t(x):
        return "WRONG" if rng.random() < 0.5 else x
    rel = Relation("sometimes wrong", transform=t, assertion=consistent_pick())
    rep = check(sys, "RIGHT", [rel], samples=20, baseline_runs=1)
    stat = next(s for s in rep.relation_stats if s.name == "sometimes wrong")
    assert stat.trials == 20
    assert 1 <= stat.violations < 20
