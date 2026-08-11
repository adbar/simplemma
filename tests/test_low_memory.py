import pytest

from simplemma import (
    in_target_language,
    is_known,
    langdetect,
    lemmatize,
    text_lemmatizer,
)
from simplemma.lemmatizer import _legacy_lemmatizer_for
from simplemma.strategies import (
    DEFAULT_DICTIONARY_FACTORY,
    LOW_MEMORY_DICTIONARY_FACTORY,
    DefaultStrategy,
    DictionaryFactory,
    StreamDictionaryFactory,
)


def _factory_of(strategy: DefaultStrategy) -> DictionaryFactory:
    return strategy._dictionary_lookup._dictionary_factory


def test_low_memory_factory_is_stream_backend() -> None:
    assert isinstance(LOW_MEMORY_DICTIONARY_FACTORY, StreamDictionaryFactory)


def test_default_strategy_low_memory_conflicts_with_explicit_factory() -> None:
    with pytest.raises(ValueError, match="low_memory"):
        DefaultStrategy(dictionary_factory=StreamDictionaryFactory(), low_memory=True)


def test_low_memory_actually_switches_backend() -> None:
    assert _factory_of(DefaultStrategy()) is DEFAULT_DICTIONARY_FACTORY
    for strategy in (
        DefaultStrategy(low_memory=True),
        _legacy_lemmatizer_for(False, True)._lemmatization_strategy,
        _legacy_lemmatizer_for(True, True)._lemmatization_strategy,
    ):
        assert _factory_of(strategy) is LOW_MEMORY_DICTIONARY_FACTORY  # type: ignore[arg-type]


def test_default_strategy_low_memory_matches_default() -> None:
    default = DefaultStrategy()
    low_memory = DefaultStrategy(low_memory=True)
    for token, lang in [("doughnuts", "en"), ("Häuser", "de"), ("alikaa", "sw")]:
        assert low_memory.get_lemma(token, lang) == default.get_lemma(token, lang)


@pytest.mark.parametrize("greedy", [False, True])
def test_lemmatize_low_memory_matches_default(greedy: bool) -> None:
    for token, lang in [("doughnuts", "en"), ("alikaa", "sw")]:
        assert lemmatize(token, lang, greedy=greedy, low_memory=True) == lemmatize(
            token, lang, greedy=greedy
        )


def test_text_lemmatizer_low_memory_matches_default() -> None:
    text = "the doughnuts are quite good"
    assert text_lemmatizer(text, "en", low_memory=True) == text_lemmatizer(text, "en")


def test_is_known_low_memory_matches_default() -> None:
    for token in ["doughnuts", "zzzznotaword"]:
        assert is_known(token, "en", low_memory=True) == is_known(token, "en")


def test_in_target_language_low_memory_matches_default() -> None:
    text = "the doughnuts are quite good"
    assert in_target_language(text, "en", low_memory=True) == in_target_language(
        text, "en"
    )


def test_langdetect_low_memory_matches_default() -> None:
    text = "the doughnuts are quite good"
    assert langdetect(text, ("en", "de"), low_memory=True) == langdetect(
        text, ("en", "de")
    )


def test_both_backends_expose_the_same_mapping_interface() -> None:
    """A consumer written against one factory must work with the other: both
    dictionaries are Mappings whose items() is a sized, re-iterable view."""
    for factory in (DEFAULT_DICTIONARY_FACTORY, LOW_MEMORY_DICTIONARY_FACTORY):
        items = factory.get_dictionary("en").items()
        assert len(items) == len(list(items)) == len(list(items))


def test_legacy_lemmatizers_are_cached_per_key() -> None:
    assert _legacy_lemmatizer_for(False, True) is _legacy_lemmatizer_for(False, True)
    assert _legacy_lemmatizer_for(False, True) is not _legacy_lemmatizer_for(
        False, False
    )
