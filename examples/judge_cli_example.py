"""Template for `wobbly judge <this file>`.

Define two things and point the CLI at this file:

    wobbly judge examples/judge_cli_example.py

  cases       a list of {"question", "answers": [A, B]} pairs
  judge(case) your grader — returns "A"/"B" (or the chosen answer's text)

Replace the body of judge() with a call to YOUR model. The placeholder below
always picks whichever answer is listed first — a pure position bias — so running
the command on this file reports every pair as flipped. Swap it for your real
judge to see how often *its* verdict changes when the two answers trade places.
No answer key required.
"""

cases = [
    {"question": "Which explanation of recursion is better?",
     "answers": ["A function that calls itself until it hits a base case.",
                 "Solving a problem by reducing it to a smaller instance of itself."]},
    {"question": "Which tagline is better for a water bottle?",
     "answers": ["Hydrate responsibly.", "Sip sustainably."]},
    {"question": "Which is a better name for a note-taking app?",
     "answers": ["Jotly", "NoteNest"]},
]


def judge(case):
    # TODO: replace with your real judge — a call to your model that returns
    # "A" or "B" (or the exact text of the answer it prefers).
    return "A"   # placeholder: always the first option -> position bias, flips every pair
