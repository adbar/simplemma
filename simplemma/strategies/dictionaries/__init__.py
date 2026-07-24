"""Dictionary-based lemmatization strategy."""

from functools import lru_cache

from .dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultDictionaryFactory,
    DictionaryFactory,
)
from .stream_dictionary_factory import StreamDictionaryFactory
from .trie_dictionary_factory import TrieDictionaryFactory


def make_low_memory_factory() -> DictionaryFactory:
    """The most memory-frugal backend. For steady-state RAM with faster
    lookups, pass `dictionary_factory=TrieDictionaryFactory()` instead."""
    return StreamDictionaryFactory()


@lru_cache(maxsize=None)
def _shared_low_memory_factory() -> DictionaryFactory:
    """Shared across low_memory call sites so each doesn't reload every dict."""
    return make_low_memory_factory()


__all__ = [
    "DEFAULT_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "StreamDictionaryFactory",
    "TrieDictionaryFactory",
    "make_low_memory_factory",
]
