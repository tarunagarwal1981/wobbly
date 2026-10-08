"""Point wobbly at a REAL Claude model and measure order / position-bias flip-rate —
opt-in, no answer key used. Two label-free tests:

  mcq   — ask the model to pick the correct option, rotate the options, see if the
          chosen option changes (order_invariant, coverage="rotate").
  judge — the stronger, well-documented setup: ask which of two responses is better,
          swap their order, see if the verdict flips (wobbly.judge_bias — its
          reference usage).

In both, the system-under-test returns the chosen ITEM (resolved from the letter),
so re-lettering under a shuffle is never mistaken for a flip. No "right" answer is
ever supplied — we only measure self-consistency under reordering.

NOT on the offline path: the frozen demo (scripts/run_blind.py), the package, and
the test suite never import this. It is not shipped in the wheel.

Setup (run it YOURSELF; your key never leaves your machine):
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/live_check.py
    # optional: WOBBLY_MODEL=claude-... WOBBLY_SAMPLES=8 WOBBLY_BASELINE=4
    #           WOBBLY_MAX_CALLS=1500 WOBBLY_MODE=both|mcq|judge
    unset ANTHROPIC_API_KEY
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wobbly import check, order_invariant, consistent_pick, judge_bias

MODEL = os.environ.get("WOBBLY_MODEL", "claude-haiku-4-5-20251001")
SAMPLES = int(os.environ.get("WOBBLY_SAMPLES", "8"))
BASELINE = int(os.environ.get("WOBBLY_BASELINE", "4"))
MAX_CALLS = int(os.environ.get("WOBBLY_MAX_CALLS", "1500"))
MODE = os.environ.get("WOBBLY_MODE", "both").lower()  # both | mcq | judge

# --- MCQ cases: unambiguous factual questions (order must not change the pick) --
MCQS = [
    {"question": "Which planet is closest to the Sun?",
     "options": ["Mercury", "Venus", "Earth", "Mars"]},
    {"question": "What is the capital of Australia?",
     "options": ["Canberra", "Sydney", "Melbourne", "Perth"]},
    {"question": "Who wrote the play 'Hamlet'?",
     "options": ["William Shakespeare", "Christopher Marlowe", "Charles Dickens", "Geoffrey Chaucer"]},
    {"question": "Which element has the chemical symbol 'Fe'?",
     "options": ["Iron", "Fluorine", "Francium", "Lead"]},
    {"question": "In which year did World War II end?",
     "options": ["1945", "1939", "1918", "1950"]},
    {"question": "Which of these is a prime number?",
     "options": ["17", "21", "27", "33"]},
]

# --- JUDGE cases: two comparable responses (where position bias lives) ----------
# Most are close-in-quality on purpose; the last three have a clear winner
# (controls) so we can confirm the tool only flips on genuine close calls.
JUDGE_CASES = [
    {"question": "Suggest a name for a focus/productivity app.",
     "answers": ["FocusFlow", "TaskNest"]},
    {"question": "Give one tip for better sleep.",
     "answers": ["Avoid screens for an hour before bed.",
                 "Keep a consistent sleep and wake schedule."]},
    {"question": "Explain recursion in one sentence.",
     "answers": ["A function that calls itself until it hits a base case.",
                 "Solving a problem by reducing it to a smaller instance of the same problem."]},
    {"question": "Recommend a first programming language for a beginner.",
     "answers": ["Python, for its clean and readable syntax.",
                 "JavaScript, since it runs in every web browser."]},
    {"question": "Write a short motivational line.",
     "answers": ["Progress, not perfection.", "Small steps, every single day."]},
    {"question": "Describe the taste of coffee to someone who has never had it.",
     "answers": ["Bitter, rich, and slightly roasted.",
                 "A warm, slightly bitter drink with earthy, roasted notes."]},
    {"question": "Suggest a healthy breakfast.",
     "answers": ["Oatmeal with fruit and nuts.", "Greek yogurt with berries and a little honey."]},
    {"question": "Suggest a tagline for an eco-friendly water bottle.",
     "answers": ["Hydrate responsibly.", "Sip sustainably."]},
    {"question": "Give one piece of advice for a first job interview.",
     "answers": ["Research the company thoroughly beforehand.",
                 "Prepare a few thoughtful questions to ask them."]},
    {"question": "Recommend a way to learn a new language.",
     "answers": ["Practice speaking with a native speaker daily.",
                 "Review spaced-repetition flashcards every day."]},
    {"question": "Which is a better name for a note-taking app?",
     "answers": ["Jotly", "NoteNest"]},
    {"question": "Explain what an API is, briefly.",
     "answers": ["A way for two programs to talk to each other.",
                 "A set of rules that lets software components communicate."]},
    {"question": "Suggest a relaxing weekend hobby.",
     "answers": ["Learn to cook a new cuisine.", "Start hiking local trails."]},
    {"question": "Write a short thank-you note opener.",
     "answers": ["Thank you so much for your thoughtfulness.",
                 "I really appreciate your kindness."]},
    {"question": "Recommend a productivity technique.",
     "answers": ["Try the Pomodoro method.", "Time-block your calendar each morning."]},
    {"question": "Suggest a name for a black cat.",
     "answers": ["Shadow", "Midnight"]},
    {"question": "Recommend a beginner-friendly houseplant.",
     "answers": ["A snake plant — nearly impossible to kill.",
                 "A pothos — thrives with very little attention."]},
    {"question": "Give a short tip for writing clearer emails.",
     "answers": ["Put the ask in the first sentence.",
                 "Use short paragraphs and a clear subject line."]},
    {"question": "Which is the clearer git commit message?",   # control: 2nd clearly better
     "answers": ["fix bug", "fix off-by-one error in pagination offset"]},
    {"question": "Which is a more informative error message?",   # control: 2nd clearly better
     "answers": ["error", "ValueError: expected int, got str (line 42)"]},
    {"question": "Which README line is more helpful to a new user?",   # control: 2nd clearly better
     "answers": ["This is a tool.",
                 "Install with `pip install wobbly`; finds wrong LLM outputs with no labels."]},
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
        # No temperature override: newer models (e.g. claude-sonnet-5) DEPRECATE the
        # parameter and return HTTP 400 if it's sent. We do NOT assume determinism —
        # wobbly's baseline-variance control samples the clean input BASELINE times
        # to learn the model's own flicker, and flags a reorder only BEYOND it.
        msg = client.messages.create(
            model=MODEL, max_tokens=8,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(b, "text", "") for b in msg.content).strip()

    return call


def _capped(call, max_calls):
    """Count calls and enforce a hard cap. NO caching: repeated calls on the same
    input must genuinely re-sample the model, which is how the baseline captures
    its run-to-run variance (caching would collapse the baseline to zero spread)."""
    n = {"c": 0}

    def wrapped(x):
        if n["c"] >= max_calls:
            raise RuntimeError(f"exceeded max_calls={max_calls}")
        n["c"] += 1
        return call(x)

    wrapped.calls = lambda: n["c"]
    return wrapped


def _mcq_prompt(mcq) -> str:
    opts = "\n".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(mcq["options"]))
    return (f"{mcq['question']}\n{opts}\n\n"
            f"Answer with ONLY the letter of the correct option.")


def _judge_prompt(case) -> str:
    a, b = case["answers"]
    return (f"Question: {case['question']}\n\n"
            f"Response A: {a}\nResponse B: {b}\n\n"
            f"Which response is better? Answer with ONLY the letter A or B.")


def run_mcq(call):
    """Order-invariance over every MCQ, aggregated. A correct, order-robust model
    scores 0% — that is the control that proves the method isn't flagging noise."""
    def model_pick(mcq):
        resp = call(_mcq_prompt(mcq)).upper()
        for i in range(len(mcq["options"])):
            if chr(65 + i) in resp:
                return mcq["options"][i]
        return resp[:20]

    rows = []
    viol = trials = 0
    for mcq in MCQS:
        rel = order_invariant(field="options", assertion=consistent_pick(), coverage="rotate")
        rep = check(model_pick, mcq, [rel], samples=SAMPLES, baseline_runs=BASELINE,
                    subject=mcq["question"])
        s = rep.relation_stats[0]
        viol += s.violations
        trials += s.trials
        rows.append((mcq["question"], rep.baseline[0], rep.broke, s.violations, s.trials))

    flipped = sum(1 for r in rows if r[2])
    print("== MCQ option-order ==")
    for q, base, broke, v, t in rows:
        rate = f"{v}/{t}" if t else "n/a"
        print(f"  {'FLIP' if broke else 'ok  '} {rate:>5}  {q[:48]:48}  base={str(base)[:16]!r}")
    agg = 100 * viol / trials if trials else 0.0
    print(f"  -> {flipped}/{len(MCQS)} MCQs changed answer under reordering | "
          f"aggregate {viol}/{trials} ({agg:.0f}%)\n")


def run_judge(call):
    """Pairwise A/B judge, swap order, measure verdict flips (wobbly.judge_bias)."""
    res = judge_bias(lambda case: call(_judge_prompt(case)), JUDGE_CASES,
                     samples=SAMPLES, baseline_runs=BASELINE)
    print("== JUDGE pairwise-order (A vs B) ==")
    print(res.summary())
    print()


def main():
    if MODE not in ("both", "mcq", "judge"):
        sys.exit(f"WOBBLY_MODE must be both|mcq|judge, got {MODE!r}")
    anthropic = _require_anthropic()
    call = _capped(_make_call(anthropic), MAX_CALLS)
    print(f"model: {MODEL}   (samples/item: {SAMPLES}, baseline/item: {BASELINE}, mode: {MODE})\n")
    if MODE in ("both", "mcq"):
        run_mcq(call)
    if MODE in ("both", "judge"):
        run_judge(call)
    print(f"(total model API calls: {call.calls()})  No answer key was used.")


if __name__ == "__main__":
    main()
