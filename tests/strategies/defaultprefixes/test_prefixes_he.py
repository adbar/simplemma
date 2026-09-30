from simplemma.strategies import PrefixDecompositionStrategy

_STRATEGY = PrefixDecompositionStrategy()


def test_prefixes_he() -> None:
    # ב (in/at/with) + בית (house)
    assert _STRATEGY.get_lemma("בבית", "he") == "בית"


def test_prefixes_he_stem_floor() -> None:
    """A 2-letter token must not strip to one letter (בצ -> צ -> צפון)."""
    assert _STRATEGY.get_lemma("בצ", "he") is None


def test_prefixes_he_pointed_input() -> None:
    """The token is canonicalized before prefix matching."""
    assert _STRATEGY.get_lemma("בַּבַּיִת", "he") == "בית"
