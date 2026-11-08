"""Point wobbly's position_sweep at a REAL model and measure "lost in the middle"
on a RAG-style task — opt-in, label-free.

For each question there is ONE document that actually contains the answer, plus
plausible distractors. We slide the answer-bearing document through every position
(wobbly.position_sweep) and ask the model to answer from the documents. A correct
system gives the same answer wherever that document sits; if the answer changes
with position, that's "lost in the middle" — caught with no answer key.

The facts are INVENTED so the model cannot answer from memory — it must use the
retrieved context, which is the whole point.

NOT on the offline path; not shipped in the wheel. Needs the Anthropic SDK + key.

Setup (run it YOURSELF; your key never leaves your machine):
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/live_rag.py
    # optional: WOBBLY_MODEL=claude-... WOBBLY_BASELINE=4 WOBBLY_MAX_CALLS=2000
    unset ANTHROPIC_API_KEY
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wobbly import check, position_sweep, consistent_pick

MODEL = os.environ.get("WOBBLY_MODEL", "claude-haiku-4-5-20251001")
BASELINE = int(os.environ.get("WOBBLY_BASELINE", "4"))
MAX_CALLS = int(os.environ.get("WOBBLY_MAX_CALLS", "4000"))
# "Lost in the middle" grows with context length. Pad each question's context to
# N_DOCS with irrelevant filler so the answer-bearing doc is buried among many.
N_DOCS = int(os.environ.get("WOBBLY_RAG_DOCS", "15"))

# Generic filler: plausible world-building facts that answer NONE of the questions.
FILLER = [
    "The regional council meets on the first Monday of each quarter.",
    "Annual rainfall in the district has been rising slowly for a decade.",
    "The old tramline was decommissioned and replaced with electric buses.",
    "A weekly farmers' market sets up in the central plaza on Saturdays.",
    "The public library extended its evening hours last year.",
    "Most rooftops in the quarter are fitted with solar panels now.",
    "The river walk was repaved after the spring floods.",
    "A new recycling depot opened near the industrial estate.",
    "The symphony hall seats just under two thousand people.",
    "Cycling lanes were added to three of the main avenues.",
    "The botanical garden introduced a night-opening in summer.",
    "Street festivals draw large crowds in the warmer months.",
    "The ferry terminal added a covered waiting area.",
    "A mural project brightened several underpasses downtown.",
    "The observatory offers free public viewings twice a month.",
    "The transit app now shows live arrival times.",
    "A community orchard was planted on the eastern slope.",
    "The clock tower was restored to mark the city's centenary.",
    "The aquarium added a touch pool for school groups.",
    "A pedestrian bridge now links the two riverbanks.",
    "The night market rotates vendors every other week.",
    "The planetarium reopened after a long renovation.",
    "A fleet of electric street sweepers was introduced.",
    "The old grain silo became a climbing center.",
    "Rooftop beekeeping is quietly catching on downtown.",
    "The transit authority trialed a flat weekend fare.",
    "A seed library opened inside the main branch.",
    "The pier's arcade was refurbished over the winter.",
    "Local buses switched to a contactless payment system.",
]

# Each case: an invented fact (so the answer must come from the docs), the
# answer-bearing `key` document, and plausible distractors in the same world.
CASES = [
    {"question": "What is the access code for the Zorblex vault?",
     "answer": "7741",
     "key": "The Zorblex vault access code is 7741.",
     "distractors": [
         "The Zorblex vault was installed in the east wing in 2043.",
         "Zorblex vault maintenance is scheduled every third Tuesday.",
         "The Zorblex vault door weighs roughly 900 kilograms.",
         "Access to the Zorblex wing requires a blue clearance badge.",
     ]},
    {"question": "Who is the harbormaster of Pellani Port?",
     "answer": "Okonkwo",
     "key": "The harbormaster of Pellani Port is Dell Okonkwo.",
     "distractors": [
         "Pellani Port handles mostly grain and timber shipments.",
         "The Pellani Port lighthouse was repainted last spring.",
         "Ferries leave Pellani Port every forty minutes in summer.",
         "Pellani Port has fourteen deep-water berths.",
     ]},
    {"question": "What is the maximum depth of Lake Virenth, in meters?",
     "answer": "212",
     "key": "Lake Virenth reaches a maximum depth of 212 meters.",
     "distractors": [
         "Lake Virenth freezes along its northern shore each winter.",
         "Three rivers feed into Lake Virenth from the western hills.",
         "Lake Virenth is a popular spot for migratory cranes.",
         "The surface area of Lake Virenth is about 60 square kilometers.",
     ]},
    {"question": "Which mineral powers the Thessy reactor?",
     "answer": "cerulite",
     "key": "The Thessy reactor is powered by cerulite.",
     "distractors": [
         "The Thessy reactor came online after a six-year build.",
         "Thessy reactor coolant is cycled through two outer loops.",
         "The Thessy site employs around four hundred technicians.",
         "The Thessy reactor supplies power to three nearby districts.",
     ]},
    {"question": "What is the call sign of the research vessel Maribel?",
     "answer": "QX-9",
     "key": "The research vessel Maribel uses the call sign QX-9.",
     "distractors": [
         "The Maribel was launched from the Harlan shipyard.",
         "The Maribel carries a crew of twenty-two scientists.",
         "The Maribel specializes in deep-sea sediment sampling.",
         "The Maribel's hull is reinforced for polar ice.",
     ]},
    {"question": "On which floor is the Okavia archive located?",
     "answer": "14",
     "key": "The Okavia archive is located on the 14th floor.",
     "distractors": [
         "The Okavia archive holds records dating back two centuries.",
         "Entry to the Okavia archive requires a reader's pass.",
         "The Okavia archive uses a climate-controlled storage system.",
         "The Okavia building has a rooftop garden open to staff.",
     ]},
    {"question": "What is the name of Dr. Honce's assistant?",
     "answer": "Valdez",
     "key": "Dr. Honce's assistant is named Priya Valdez.",
     "distractors": [
         "Dr. Honce lectures on marine botany each autumn.",
         "Dr. Honce's lab is funded by the Merrow Foundation.",
         "Dr. Honce published a well-known paper on kelp forests.",
         "Dr. Honce keeps office hours on Thursday mornings.",
     ]},
    {"question": "How many moons orbit the planet Dassen?",
     "answer": "three",
     "key": "The planet Dassen has three moons.",
     "distractors": [
         "Dassen has a faint ring of ice particles.",
         "A year on Dassen lasts about 400 local days.",
         "Dassen's atmosphere is rich in methane.",
         "Dassen was first charted by the Corvus survey.",
     ]},
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
        # No temperature: newer models deprecate it. Baseline-variance handles noise.
        msg = client.messages.create(
            model=MODEL, max_tokens=16,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(b, "text", "") for b in msg.content).strip()

    return call


def _capped(call, max_calls):
    n = {"c": 0}

    def wrapped(x):
        if n["c"] >= max_calls:
            raise RuntimeError(f"exceeded max_calls={max_calls}")
        n["c"] += 1
        return call(x)

    wrapped.calls = lambda: n["c"]
    return wrapped


def _norm(s: str) -> str:
    """Label-free normalization: collapse to alphanumerics so formatting noise
    ('QX-9' vs 'QX 9') isn't mistaken for a different answer."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _rag_prompt(case) -> str:
    docs = "\n".join(f"- {d}" for d in case["docs"])
    return (f"Use ONLY the documents below to answer.\n\nDocuments:\n{docs}\n\n"
            f"Question: {case['question']}\n"
            f"Answer with ONLY the value, no other words.")


def run_rag(call):
    rows = []
    viol = trials = 0
    correct_base = 0
    for ci, c in enumerate(CASES):
        # build an N_DOCS context: the answer doc + its distractors + rotating filler
        others = list(c["distractors"]) + FILLER[ci % len(FILLER):] + FILLER[:ci % len(FILLER)]
        docs = [c["key"]] + others[:max(1, N_DOCS - 1)]
        case = {"question": c["question"], "docs": docs}

        seen = []

        def system(mc, _seen=seen):
            a = _norm(call(_rag_prompt(mc)))
            _seen.append(a)
            return a

        rel = position_sweep(field="docs", pivot_match=lambda d, k=c["key"]: d == k,
                             assertion=consistent_pick())
        rep = check(system, case, [rel], samples=len(case["docs"]), baseline_runs=BASELINE,
                    subject=c["question"])
        s = rep.relation_stats[0]
        viol += s.violations
        trials += s.trials
        base = rep.baseline[0] if rep.baseline else ""
        base_ok = _norm(c["answer"]) in base
        correct_base += 1 if base_ok else 0
        distinct = sorted(set(seen))
        rows.append((c["question"], base, rep.broke, s.violations, s.trials, base_ok, distinct))

    flipped = sum(1 for r in rows if r[2])
    print("== RAG position-sweep (slide the answer doc through every position) ==")
    print(f"{'question':48}  base answer      flip-rate   base-correct")
    print("-" * 92)
    for q, base, broke, v, t, ok, distinct in rows:
        rate = f"{v}/{t}" if t else "n/a"
        print(f"{q[:48]:48}  {str(base)[:14]:14}  {rate:>7}{'  FLIPS' if broke else '      '}   {'yes' if ok else 'NO'}")
    print("-" * 92)
    agg = 100 * viol / trials if trials else 0.0
    print(f"{flipped}/{len(CASES)} questions changed answer when the relevant doc moved | "
          f"aggregate {viol}/{trials} ({agg:.0f}%)")
    # Honesty check: show the DISTINCT answers for flagged questions, so a real
    # position flip ('three' -> '4') can be told apart from formatting noise
    # ('3' vs 'three'). Decide by eye before trusting the flip-rate.
    flaggers = [(q, d) for q, _b, broke, _v, _t, _ok, d in rows if broke]
    if flaggers:
        print("\nflagged questions — distinct answers seen (inspect: real flip vs formatting):")
        for q, d in flaggers:
            print(f"  {q[:52]:52}  {d}")
    print(f"base-position accuracy: {correct_base}/{len(CASES)} answered correctly with the doc in slot 0")
    print("(self-consistency measured with NO answer key; base-correct is a bonus check using the planted facts)")


def main():
    anthropic = _require_anthropic()
    call = _capped(_make_call(anthropic), MAX_CALLS)
    print(f"model: {MODEL}   (baseline/item: {BASELINE})\n")
    try:
        run_rag(call)
    except anthropic.AuthenticationError:
        sys.exit("\nAuthentication failed (401): export a current ANTHROPIC_API_KEY and retry.")
    except anthropic.APIError as e:
        sys.exit(f"\nAnthropic API error ({getattr(e, 'status_code', '?')}): {e}")
    print(f"\n(total model API calls: {call.calls()})  No answer key was used to flag.")


if __name__ == "__main__":
    main()
