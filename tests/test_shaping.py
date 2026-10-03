import pytest
from wobbly._shaping import resolve_shaper


def test_field_shaper_gets_and_sets_keeping_other_keys():
    getter, setter, label = resolve_shaper(field="opts")
    x = {"q": "keep me", "opts": [1, 2]}
    assert getter(x) == [1, 2]
    out = setter(x, [9])
    assert out == {"q": "keep me", "opts": [9]}
    assert "opts" in label


def test_accessor_shaper():
    getter, setter, label = resolve_shaper(get=lambda t: t[1], set=lambda t, v: (t[0], v))
    assert getter(("a", [1])) == [1]
    assert setter(("a", [1]), [2]) == ("a", [2])


def test_identity_shaper():
    getter, setter, label = resolve_shaper()
    assert getter([1, 2]) == [1, 2]
    assert setter([1, 2], [3]) == [3]


def test_requires_both_get_and_set():
    with pytest.raises(ValueError):
        resolve_shaper(get=lambda x: x)
