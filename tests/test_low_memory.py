from unittest.mock import patch

import pytest

from simplemma import (
    in_target_language,
    is_known,
    langdetect,
    lemmatize,
    text_lemmatizer,
)
from simplemma.language_detector import _default_strategy_for
from simplemma.lemmatizer import _legacy_dictionary_lookup_for, _legacy_lemmatizer_for
from simplemma.strategies import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultStrategy,
    DictionaryFactory,
    StreamDictionaryFactory,
    TrieDictionaryFactory,
)
from simplemma.strategies.dictionaries import make_low_memory_factory
from simplemma.strategies.dictionaries.trie_dictionary_factory import (
    _TRIE_DEPS_AVAILABLE,
)


def _factory_of(strategy: DefaultStrategy) -> DictionaryFactory:
    return strategy._dictionary_lookup._dictionary_factory


@pytest.mark.skipif(not _TRIE_DEPS_AVAILABLE, reason="marisa_trie not installed")
def test_make_low_memory_factory_prefers_trie_when_available() -> None:
    assert isinstance(make_low_memory_factory(), TrieDictionaryFactory)


def test_make_low_memory_factory_falls_back_to_stream_without_trie_deps() -> None:
    with patch(
        "simplemma.strategies.dictionaries.trie_dictionary_factory._TRIE_DEPS_AVAILABLE",
        False,
    ):
        assert isinstance(make_low_memory_factory(), StreamDictionaryFactory)


def test_default_strategy_low_memory_conflicts_with_explicit_factory() -> None:
    with pytest.raises(ValueError, match="low_memory"):
        DefaultStrategy(dictionary_factory=StreamDictionaryFactory(), low_memory=True)


def test_low_memory_actually_switches_backend() -> None:
    # Parity can't catch a silently-ignored flag, so assert the backend swapped.
    assert _factory_of(DefaultStrategy()) is DEFAULT_DICTIONARY_FACTORY
    for strategy in (
        DefaultStrategy(low_memory=True),
        _legacy_lemmatizer_for(False, True)._lemmatization_strategy,
        _default_strategy_for(False, low_memory=True),
    ):
        factory = _factory_of(strategy)  # type: ignore[arg-type]
        assert factory is not DEFAULT_DICTIONARY_FACTORY
        assert isinstance(factory, (StreamDictionaryFactory, TrieDictionaryFactory))
    assert _legacy_dictionary_lookup_for(True)._dictionary_factory is not (
        DEFAULT_DICTIONARY_FACTORY
    )


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


def test_legacy_singletons_are_cached_per_key() -> None:
    assert _legacy_lemmatizer_for(False, True) is _legacy_lemmatizer_for(False, True)
    assert _legacy_lemmatizer_for(False, True) is not _legacy_lemmatizer_for(
        False, False
    )
    assert _legacy_dictionary_lookup_for(True) is _legacy_dictionary_lookup_for(True)
    assert _default_strategy_for(False, low_memory=True) is _default_strategy_for(
        False, low_memory=True
    )
