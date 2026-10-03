def test_plan3_symbols_exported():
    from wobbly import (distractor_robust, formatting_invariant,
                        paraphrase_invariant, equivalent)
    from wobbly.core import Relation
    from wobbly.assertions import Assertion
    assert isinstance(distractor_robust(field="t"), Relation)
    assert isinstance(formatting_invariant(field="t"), Relation)
    assert isinstance(paraphrase_invariant(field="t", variants=["x"]), Relation)
    assert isinstance(equivalent(lambda s: [0.0]), Assertion)
