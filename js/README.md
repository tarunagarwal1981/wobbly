# @tarunagarwal1981/wobbly

**Metamorphic testing for AI outputs — find wrong answers without an answer key.**

This package reserves the `wobbly` name on npm under a scope. **wobbly is a Python library
today** — a JS port may follow.

```bash
pip install wobbly
```

- Repo: https://github.com/tarunagarwal1981/wobbly
- Writeup: [Your LLM extracted 10,000 numbers — which ones are wrong?](https://medium.com/towards-artificial-intelligence/your-llm-extracted-10-000-numbers-which-ones-are-wrong-7a5d54050dd3)

It flags wrong outputs with no labels by checking invariants: reorder a receipt's lines, the
total must not change; if the answer flips, that's a bug — found without ground truth.
