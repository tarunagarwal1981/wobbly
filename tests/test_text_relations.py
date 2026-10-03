import pytest
from wobbly import check
from wobbly.text import distractor_robust, formatting_invariant, paraphrase_invariant


def test_distractor_flags_a_distractible_system():
    sys = lambda x: "spam" if "weather" in x["text"].lower() else "ham"
    rel = distractor_robust(field="text", distractor="By the way, the weather is nice.")
    rep = check(sys, {"text": "please classify this"}, [rel], samples=5, baseline_runs=1)
    assert rep.broke is True


def test_distractor_passes_robust_system():
    rel = distractor_robust(field="text")
    rep = check(lambda x: "ham", {"text": "hello"}, [rel], samples=5, baseline_runs=1)
    assert rep.broke is False


def test_formatting_flags_whitespace_sensitive_system():
    sys = lambda x: len(x["text"])
    rel = formatting_invariant(field="text")
    rep = check(sys, {"text": "a b c"}, [rel], samples=6, baseline_runs=1)
    assert rep.broke is True


def test_formatting_passes_whitespace_robust_system():
    sys = lambda x: x["text"].strip().split()[0]
    rel = formatting_invariant(field="text")
    rep = check(sys, {"text": "hello world"}, [rel], samples=6, baseline_runs=1)
    assert rep.broke is False


def test_paraphrase_with_variants():
    def sys(x):
        return "A" if x["instruction"] == "pick the first" else "B"
    rel = paraphrase_invariant(field="instruction",
                               variants=["choose the first one", "select item one"])
    rep = check(sys, {"instruction": "pick the first"}, [rel], samples=4, baseline_runs=1)
    assert rep.broke is True


def test_paraphrase_requires_variants_or_callable():
    with pytest.raises(ValueError):
        paraphrase_invariant(field="instruction")
