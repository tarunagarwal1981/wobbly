"""Point wobbly at a REAL Claude model — opt-in live validation of the hero relations.

This is the one test the offline suite can't do: confirm wobbly catches a real
model's real order / paraphrase sensitivity, with no answer key. It needs the
Anthropic SDK and an API key and makes a few (bounded) paid calls.

NOT on the offline path: the frozen demo (scripts/run_blind.py), the package, and
the test suite never import this. It is not shipped in the wheel.

Setup:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/live_check.py
    # optional: WOBBLY_MODEL=claude-... WOBBLY_MAX_CALLS=40
    # optional: WOBBLY_MODE=mcq (default) | judge

Modes:
  mcq   (default)
    1. order_invariant      — does rotating the MCQ options change the model's pick?
    2. paraphrase_invariant — does rewording the instruction change the pick?
  judge
    judge_bias — does the model, acting as an A/B judge, change its pick when the
    two answers swap places? (the reference usage of wobbly.judge_bias)

Fairness note: reordering the options re-letters them, so "A" means a different
option each time. The system under test therefore returns the OPTION TEXT the
model chose (resolved from its letter), not the letter — so a flag means the model
genuinely changed its answer, not that the letters moved.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wobbly import (check, order_invariant, paraphrase_invariant, cached_system,
                    consistent_pick, judge_bias)

MODEL = os.environ.get("WOBBLY_MODEL", "claude-haiku-4-5-20251001")
MAX_CALLS = int(os.environ.get("WOBBLY_MAX_CALLS", "40"))
MODE = os.environ.get("WOBBLY_MODE", "mcq").lower()

# Close calls: two plausible answers, no objectively right one — where a judge's
# position bias shows. judge_bias is label-free, so no "correct" side is needed.
JUDGE_CASES = [
    {"question": "Which product name is better for a focus app?",
     "answers": ["FocusFlow", "TaskNest"]},
    {"question": "Which sleep tip is better?",
     "answers": ["Avoid screens before bed.", "Keep a consistent schedule."]},
    {"question": "Which opening line is stronger?",
     "answers": ["Every great project starts with a question.",
                 "Let's talk about how projects begin."]},
]


def _require_anthropic():
    try:
        import anthropic
    except ImportError:
        sys.exit("This script needs the Anthropic SDK:\n    pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY to run the live check (it makes paid API calls).")
    return anthropic


def _make_call(anthropic):
    client = anthropic.Anthropic()

    def call(prompt: str) -> str:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=8,
            temperature=0.0,  # deterministic baseline; order/paraphrase are the only variables
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(b, "text", "") for b in msg.content).strip()

    return call


def _mcq_prompt(mcq) -> str:
    opts = "\n".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(mcq["options"]))
    return (f"{mcq['instruction']}\n\n{mcq['question']}\n{opts}\n\n"
            f"Answer with ONLY the letter of the correct option.")


def _judge_prompt(case) -> str:
    a, b = case["answers"]
    return (f"{case['question']}\n\nA. {a}\nB. {b}\n\n"
            f"Answer with ONLY the letter of the better option.")


def run_judge(call):
    # judge_bias resolves the model's letter to the chosen answer text itself, so
    # re-lettering under the swap is never counted as a flip.
    print(f"model     : {MODEL}")
    print()
    res = judge_bias(lambda case: call(_judge_prompt(case)), JUDGE_CASES,
                     samples=8, baseline_runs=2)
    print(res.summary())
    print()
    print(f"(total model calls: {call.calls()})  No answer key was used.")


def main():
    if MODE not in ("mcq", "judge"):
        sys.exit(f"WOBBLY_MODE must be 'mcq' or 'judge', got {MODE!r}")
    anthropic = _require_anthropic()
    call = cached_system(_make_call(anthropic), max_calls=MAX_CALLS)
    if MODE == "judge":
        return run_judge(call)

    def model_pick(mcq):
        """Return the OPTION TEXT the model chose (resolved from its letter)."""
        resp = call(_mcq_prompt(mcq)).upper()
        for i in range(len(mcq["options"])):
            if chr(65 + i) in resp:
                return mcq["options"][i]
        return resp[:20]

    mcq = {
        "instruction": "You are a careful exam grader.",
        "question": "Which of these is a mammal?",
        "options": ["A dolphin", "A shark", "A tuna", "An octopus"],
    }

    print(f"model     : {MODEL}")
    print(f"base pick : {model_pick(mcq)!r}")
    print()

    order_rel = order_invariant(field="options", assertion=consistent_pick(),
                                coverage="rotate")
    rep1 = check(model_pick, mcq, [order_rel], samples=8, baseline_runs=2, subject="order")
    print(rep1.summary())
    if rep1.broke:
        c = rep1.counterexamples[0]
        print(f"  -> rotating the options changed the pick: {c.before!r} -> {c.after!r}")
    print()

    para_rel = paraphrase_invariant(
        field="instruction",
        variants=[
            "You are a meticulous biology teacher.",
            "Answer as a knowledgeable zoologist.",
            "Be precise and strictly factual.",
        ],
        assertion=consistent_pick(),
    )
    rep2 = check(model_pick, mcq, [para_rel], samples=3, baseline_runs=2, subject="paraphrase")
    print(rep2.summary())
    if rep2.broke:
        c = rep2.counterexamples[0]
        print(f"  -> rewording the instruction changed the pick: {c.before!r} -> {c.after!r}")
    print()
    print(f"(total model calls: {call.calls()})  No answer key was used.")


if __name__ == "__main__":
    main()
