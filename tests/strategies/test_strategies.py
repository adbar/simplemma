from simplemma.dictionary_factory import DictionaryFactory
from simplemma.strategies.dictionary_lookup import DictionaryLookupStrategy
from simplemma.strategies.hyphen_removal import HyphenRemovalStrategy
from simplemma.strategies.default import DefaultStrategy
from simplemma.strategies.greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from simplemma.strategies.affix_decomposition import AffixDecompositionStrategy


def test_search() -> None:
    """Test simple and greedy dict search."""
    dictionary_factory = DictionaryFactory()
    dictionaries = dictionary_factory.get_dictionaries(("en",))
    enDict = dictionaries["en"]
    assert DictionaryLookupStrategy().get_lemma("ignorant", "en", enDict) == "ignorant"
    assert DictionaryLookupStrategy().get_lemma("Ignorant", "en", enDict) == "ignorant"

    dictionaries = dictionary_factory.get_dictionaries(("de",))
    deDict = dictionaries["de"]
    assert DictionaryLookupStrategy().get_lemma("dritte", "en", deDict) == "dritt"
    assert DictionaryLookupStrategy().get_lemma("Dritte", "en", deDict) == "Dritter"

    assert (
        HyphenRemovalStrategy().get_lemma("magni-ficent", "en", enDict) == "magnificent"
    )
    assert HyphenRemovalStrategy().get_lemma("magni-ficents", "en", enDict) is None

    # assert simplemma.simplemma._greedy_dictionary_lookup('Ignorance-Tests', enDict) == 'Ignorance-Test'
    # don't lemmatize numbers
    assert DefaultStrategy().get_lemma("01234", "en", enDict) == "01234"

    assert (
        DefaultStrategy().get_lemma("Gender-Sternchens", "de", deDict)
        == "Gendersternchen"
    )
    assert DefaultStrategy().get_lemma("vor-bereitetes", "de", deDict) == "vorbereitet"

    assert (
        GreedyDictionaryLookupStrategy(steps=0, distance=20).get_lemma(
            "getesteten", "de", deDict
        )
        == "getesteten"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=1, distance=20).get_lemma(
            "getesteten", "de", deDict
        )
        == "getestet"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=2, distance=20).get_lemma(
            "getesteten", "de", deDict
        )
        == "testen"
    )
    assert (
        GreedyDictionaryLookupStrategy(steps=2, distance=2).get_lemma(
            "getesteten", "de", deDict
        )
        == "getestet"
    )

    assert (
        AffixDecompositionStrategy(greedy=True, limit=6).get_lemma("ccc", "de", deDict)
        is None
    )
