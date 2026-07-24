from simplemma.strategies import PrefixDecompositionStrategy


def test_prefixes_he() -> None:
    prefix_decomposition_strategy = PrefixDecompositionStrategy()
    # ב (in/at/with) + בית (house): the particle is dropped, not attached.
    assert prefix_decomposition_strategy.get_lemma("בבית", "he") == "בית"


def test_prefixes_he_stem_floor() -> None:
    """A 2-letter token must not strip to a single letter: one-letter
    abbreviation keys otherwise expand garbage (בצ -> צ -> צפון)."""
    strategy = PrefixDecompositionStrategy()
    assert strategy.get_lemma("בצ", "he") is None


def test_prefixes_he_pointed_input() -> None:
    """The token is canonicalized BEFORE prefix matching, so a pointed
    fused form still resolves. (Hebrew prefixes are all single-letter, so
    unlike ar's multi-char combos there's no fused-prefix-vs-diacritic
    interposition risk here -- this only exercises the single-letter case.)"""
    strategy = PrefixDecompositionStrategy()
    assert strategy.get_lemma("בַּבַּיִת", "he") == "בית"
