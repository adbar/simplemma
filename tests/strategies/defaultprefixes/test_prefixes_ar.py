from simplemma.strategies import PrefixDecompositionStrategy

_STRATEGY = PrefixDecompositionStrategy()


def test_prefixes_ar() -> None:
    # بال (in/with + the) + بيت (house)
    assert _STRATEGY.get_lemma("بالبيت", "ar") == "بيت"


def test_prefixes_ar_stem_floor() -> None:
    """A 2-letter token must not strip to one letter (بح -> ح -> وحى)."""
    assert _STRATEGY.get_lemma("بح", "ar") is None


def test_prefixes_ar_vocalized_input() -> None:
    """The token is canonicalized before prefix matching."""
    assert _STRATEGY.get_lemma("بِالْبَيْت", "ar") == "بيت"


def test_prefixes_ar_vocalized_compound_prefix() -> None:
    """Tashkeel inside the fused prefix بال must not block its match."""
    assert _STRATEGY.get_lemma("بِالْكِتَابِ", "ar") == "كتاب"
