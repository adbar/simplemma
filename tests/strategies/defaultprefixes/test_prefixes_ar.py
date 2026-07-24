from simplemma.strategies import PrefixDecompositionStrategy


def test_prefixes_ar() -> None:
    prefix_decomposition_strategy = PrefixDecompositionStrategy()
    # بال (in/with + the) + بيت (house): the particle is dropped, not attached.
    assert prefix_decomposition_strategy.get_lemma("بالبيت", "ar") == "بيت"


def test_prefixes_ar_stem_floor() -> None:
    """A 2-letter token must not strip to a single letter: one-letter
    keys otherwise expand garbage (بح -> ح -> وحى, a real dict entry)."""
    strategy = PrefixDecompositionStrategy()
    assert strategy.get_lemma("بح", "ar") is None


def test_prefixes_ar_vocalized_input() -> None:
    """The token is canonicalized BEFORE prefix matching (not just inside
    the dictionary lookup on the remainder), so a vocalized single-letter
    proclitic still resolves."""
    strategy = PrefixDecompositionStrategy()
    assert strategy.get_lemma("بِالْبَيْت", "ar") == "بيت"


def test_prefixes_ar_vocalized_compound_prefix() -> None:
    """A multi-character fused prefix (بال = ب + ال) has tashkeel diacritics
    interposed between its letters in real vocalized text; without folding
    BEFORE matching, the regex alternation for "بال" can never match at all
    and only the 1-char "ب" proclitic fires, leaving the article attached."""
    strategy = PrefixDecompositionStrategy()
    assert strategy.get_lemma("بِالْكِتَابِ", "ar") == "كتاب"
