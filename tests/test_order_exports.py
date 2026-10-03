def test_order_invariant_and_permute_exported():
    from wobbly import order_invariant, permute
    from wobbly.core import Relation
    rel = order_invariant(field="options")
    assert isinstance(rel, Relation)
    assert callable(permute(lambda x: x, lambda x, v: v))
