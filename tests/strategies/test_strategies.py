from simplemma.strategies import (
    AffixDecompositionStrategy,
    DefaultStrategy,
    DictionaryLookupStrategy,
    GreedyDictionaryLookupStrategy,
    HyphenRemovalStrategy,
    PrefixDecompositionStrategy,
)


def test_search() -> None:
    """Test simple and greedy dict search."""
    assert DictionaryLookupStrategy().get_lemma("ignorant", "en") == "ignorant"
    assert DictionaryLookupStrategy().get_lemma("Ignorant", "en") == "ignorant"

    assert DictionaryLookupStrategy().get_lemma("dritte", "de") == "dritt"
    assert DictionaryLookupStrategy().get_lemma("Dritte", "de") == "Dritter"

    assert HyphenRemovalStrategy().get_lemma("magni-ficent", "en") == "magnificent"
    assert HyphenRemovalStrategy().get_lemma("magni-ficents", "en") is None

    # assert simplemma.simplemma._greedy_dictionary_lookup('Ignorance-Tests') == 'Ignorance-Test'
    # don't lemmatize numbers
    assert DefaultStrategy().get_lemma("01234", "en") == "01234"

    assert DefaultStrategy().get_lemma("Gender-Sternchens", "de") == "Gendersternchen"
    assert DefaultStrategy().get_lemma("vor-bereitetes", "de") == "vorbereitet"

    assert (
        GreedyDictionaryLookupStrategy(steps=0, distance=20).get_lemma(
            "getesteten", "de"
        )
        == "getesteten"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=1, distance=20).get_lemma(
            "getesteten", "de"
        )
        == "getestet"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=2, distance=20).get_lemma(
            "getesteten", "de"
        )
        == "testen"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=2, distance=2).get_lemma(
            "getesteten", "de"
        )
        == "getestet"
    )

    assert AffixDecompositionStrategy(greedy=True).get_lemma("ccc", "de") is None

    assert PrefixDecompositionStrategy().get_lemma("auf", "de") is None
