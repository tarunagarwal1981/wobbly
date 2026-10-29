"""position_sweep — slide one item through every position ("lost in the middle")."""
from wobbly import check, position_sweep


def test_sweep_flags_position_sensitive_system():
    # always returns the item in slot 0 -> output depends on where the pivot sits
    first = lambda d: d["docs"][0]
    rel = position_sweep(field="docs", pivot=0)
    rep = check(first, {"docs": ["X", "A", "B", "C"]}, [rel], samples=4, baseline_runs=1)
    assert rep.broke is True


def test_sweep_robust_system_passes():
    # returns a fixed item by content, regardless of position
    sys = lambda d: "X"
    rel = position_sweep(field="docs", pivot=0)
    rep = check(sys, {"docs": ["X", "A", "B", "C"]}, [rel], samples=4, baseline_runs=1)
    assert rep.broke is False


def test_sweep_covers_every_position():
    seen = []

    def sys(d):
        seen.append(d["docs"].index("X"))
        return "X"

    rel = position_sweep(field="docs", pivot=0)
    check(sys, {"docs": ["X", "A", "B", "C"]}, [rel], samples=4, baseline_runs=1)
    assert set(seen[-4:]) == {0, 1, 2, 3}      # pivot visited all four positions


def test_sweep_pivot_match_locates_item():
    rel = position_sweep(field="docs", pivot_match=lambda x: x == "X")
    first = lambda d: d["docs"][0]
    rep = check(first, {"docs": ["A", "X", "B"]}, [rel], samples=3, baseline_runs=1)
    assert rep.broke is True


def test_sweep_keeps_others_relative_order():
    captured = []

    def sys(d):
        captured.append([x for x in d["docs"] if x != "X"])
        return "X"

    rel = position_sweep(field="docs", pivot=0)
    check(sys, {"docs": ["X", "A", "B", "C"]}, [rel], samples=4, baseline_runs=1)
    for others in captured:
        assert others == ["A", "B", "C"]       # non-pivot items never reorder


def test_sweep_abstains_on_singleton():
    rel = position_sweep(field="docs")
    rep = check(lambda d: d["docs"][0], {"docs": ["only"]}, [rel], samples=3, baseline_runs=1)
    assert rep.broke is False
