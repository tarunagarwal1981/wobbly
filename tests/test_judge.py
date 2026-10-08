import pytest

from wobbly import judge_bias, JudgeBiasResult
from wobbly.judge import _resolve_pick

CASES = [
    {"question": "Which name is better?", "answers": ["FocusFlow", "TaskNest"]},
    {"question": "Which tip is better?", "answers": ["Avoid screens before bed.",
                                                     "Keep a consistent schedule."]},
]


def test_letter_return_biased_judge_flips():
    judge = lambda case: "A"                       # always prefers position A
    res = judge_bias(judge, CASES, samples=8, baseline_runs=4)
    assert isinstance(res, JudgeBiasResult)
    assert res.n_cases == len(CASES)
    assert res.flipped == len(CASES)
    assert res.flip_rate > 0


def test_text_return_is_resolved_not_a_false_flip():
    def judge(case):
        return "FocusFlow" if "FocusFlow" in case["answers"] else case["answers"][0]
    cases = [{"question": "q", "answers": ["FocusFlow", "TaskNest"]}]
    res = judge_bias(judge, cases, samples=8, baseline_runs=4)
    assert res.flipped == 0


def test_letter_return_content_judge_is_not_a_false_flip():
    # Judge prefers FocusFlow and says so by LETTER; re-lettering under the swap
    # must not be counted as a flip.
    def judge(case):
        return "A" if case["answers"][0] == "FocusFlow" else "B"
    cases = [{"question": "q", "answers": ["FocusFlow", "TaskNest"]}]
    res = judge_bias(judge, cases, samples=8, baseline_runs=4)
    assert res.flipped == 0
    assert res.flip_rate == 0


def test_robust_judge_no_flips():
    def judge(case):
        return min(case["answers"])               # deterministic by content, not slot
    res = judge_bias(judge, CASES, samples=8, baseline_runs=4)
    assert res.flipped == 0


def test_per_case_detail():
    res = judge_bias(lambda c: "A", CASES[:1], samples=8, baseline_runs=2)
    row = res.per_case[0]
    assert row["question"] == "Which name is better?"
    assert row["base_pick"] == "FocusFlow"
    assert row["broke"] is True
    assert 0 < row["flips"] <= row["trials"]


def test_return_reports_only_when_asked():
    assert judge_bias(lambda c: "A", CASES, samples=4, baseline_runs=2).reports == []
    res = judge_bias(lambda c: "A", CASES, samples=4, baseline_runs=2, return_reports=True)
    assert len(res.reports) == len(CASES)


def test_custom_field():
    cases = [{"question": "q", "candidates": ["x", "y"]}]
    res = judge_bias(lambda c: "A", cases, field="candidates", samples=4, baseline_runs=2)
    assert res.flipped == 1


def test_summary_renders():
    res = judge_bias(lambda c: "A", CASES, samples=4, baseline_runs=2)
    text = res.summary()
    assert "flip" in text.lower()
    assert "Which name is better?" in text


@pytest.mark.parametrize("ret,expected", [
    ("A", "x"), ("b", "y"), ("B.", "y"), ("Answer: B", "y"),
    ("x", "x"), ("I think y is better", "y"),
])
def test_resolve_pick(ret, expected):
    assert _resolve_pick(ret, ["x", "y"]) == expected


def test_resolve_pick_ignores_letters_inside_words():
    # 'ANSWER' contains an A; only the standalone B is a pick.
    assert _resolve_pick("ANSWER: B", ["x", "y"]) == "y"


def test_resolve_pick_fallback_truncates():
    assert _resolve_pick("z" * 100, ["x", "y"]) == "z" * 40
