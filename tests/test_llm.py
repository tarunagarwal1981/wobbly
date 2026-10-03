import pytest
from wobbly.llm import cached_system


def test_caches_repeated_inputs():
    calls = {"n": 0}
    def call(x):
        calls["n"] += 1
        return x.upper()
    sys = cached_system(call)
    assert sys("hi") == "HI"
    assert sys("hi") == "HI"            # served from cache
    assert calls["n"] == 1             # underlying call made once


def test_baseline_runs_are_one_underlying_call():
    calls = {"n": 0}
    def call(x):
        calls["n"] += 1
        return "ok"
    sys = cached_system(call)
    for _ in range(5):                  # mimics baseline_runs on the same input
        sys("same")
    assert calls["n"] == 1


def test_max_calls_cap_raises():
    sys = cached_system(lambda x: x, max_calls=2)
    sys("a"); sys("b")                  # 2 distinct calls -> ok
    with pytest.raises(RuntimeError):
        sys("c")                        # 3rd distinct call -> capped


def test_custom_key():
    calls = {"n": 0}
    def call(x):
        calls["n"] += 1
        return x["q"]
    sys = cached_system(call, key=lambda x: x["q"])   # cache by the 'q' field only
    sys({"q": "same", "noise": 1})
    sys({"q": "same", "noise": 2})
    assert calls["n"] == 1
