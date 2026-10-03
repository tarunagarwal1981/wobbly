from wobbly import default_pack, consistent_pick, unchanged
from wobbly.assertions import Assertion
from wobbly.relations import total_reorder_invariant


def test_pack_relations_use_assertion_objects():
    for rel in default_pack():
        assert isinstance(rel.assertion, Assertion), rel.name


def test_consistent_pick_is_exported():
    from wobbly import consistent_pick as cp
    assert isinstance(cp(), Assertion)
