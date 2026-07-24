"""Dictionary-based lemmatization strategy."""

from .dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultDictionaryFactory,
    DictionaryFactory,
)
from .stream_dictionary_factory import StreamDictionaryFactory
from .trie_dictionary_factory import TrieDictionaryFactory

# The most memory-frugal backend, shared across low_memory call sites so each
# doesn't reload every dict. For steady-state RAM with faster lookups, pass
# `dictionary_factory=TrieDictionaryFactory()` instead.
LOW_MEMORY_DICTIONARY_FACTORY = StreamDictionaryFactory()

__all__ = [
    "DEFAULT_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "LOW_MEMORY_DICTIONARY_FACTORY",
    "StreamDictionaryFactory",
    "TrieDictionaryFactory",
]
