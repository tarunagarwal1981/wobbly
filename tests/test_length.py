"""length_invariant relation + length_bias judge helper (verbosity bias, label-free)."""
import itertools

from wobbly import check, length_invariant, length_bias
from wobbly.text import pad_text


# ---- pad_text ----------------------------------------------------------------

def test_pad_text_deterministic_and_longer():
    a = pad_text("hello world", factor=3.0)
    b = pad_text("hello world", factor=3.0)
    assert a == b                              # deterministic
    assert a.startswith("hello world")         # original kept, filler appended
    assert len(a) > len("hello world") * 2     # genuinely longer


def test_pad_text_abstains_on_empty():
    assert pad_text("") == ""


# ---- length_invariant (general relation) -------------------------------------

def test_length_invariant_flags_length_sensitive_system():
    sys = lambda d: "long" if len(d["ans"]) > 40 else "short"
    rel = length_invariant(field="ans", factor=6.0)
    rep = check(sys, {"ans": "brief"}, [rel], samples=3, baseline_runs=1)
    assert rep.broke is True


def test_length_invariant_passes_content_based_system():
    sys = lambda d: d["ans"].split()[0]        # first word — independent of length
    rel = length_invariant(field="ans", factor=6.0)
    rep = check(sys, {"ans": "mercury then more"}, [rel], samples=3, baseline_runs=1)
    assert rep.broke is False


# ---- length_bias (judge helper) ----------------------------------------------

def test_length_biased_judge_flips_when_loser_padded():
    judge = lambda case: max(case["answers"], key=len)     # prefers the longer answer
    cases = [{"question": "q", "answers": ["short", "a somewhat longer answer"]}]
    res = length_bias(judge, cases, samples=5, baseline_runs=3)
    assert res.flipped == 1                    # padding the loser makes it longest -> flips


def test_length_robust_judge_no_flip():
    judge = lambda case: min(case["answers"])  # alphabetical — length-independent
    cases = [{"question": "q", "answers": ["apple", "banana is the other one"]}]
    res = length_bias(judge, cases, samples=5, baseline_runs=3)
    assert res.flipped == 0


def test_length_bias_skips_flickery_baseline():
    counter = itertools.count()
    judge = lambda case: case["answers"][next(counter) % 2]   # alternates -> unstable
    cases = [{"question": "q", "answers": ["x", "y"]}]
    res = length_bias(judge, cases, samples=4, baseline_runs=4)
    assert res.flipped == 0
    assert res.per_case[0]["stable"] is False


def test_length_bias_summary_renders():
    judge = lambda case: max(case["answers"], key=len)
    cases = [{"question": "q", "answers": ["a", "bb"]}]
    s = length_bias(judge, cases, samples=3, baseline_runs=2).summary()
    assert "length" in s.lower()
