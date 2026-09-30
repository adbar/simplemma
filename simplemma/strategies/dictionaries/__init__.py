"""Dictionary-based lemmatization strategy."""

from .dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultDictionaryFactory,
    DictionaryFactory,
)
from .stream_dictionary_factory import StreamDictionaryFactory
from .trie_dictionary_factory import TrieDictionaryFactory

# pass TrieDictionaryFactory() instead for low RAM with faster lookups
LOW_MEMORY_DICTIONARY_FACTORY = StreamDictionaryFactory()

__all__ = [
    "DEFAULT_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "LOW_MEMORY_DICTIONARY_FACTORY",
    "StreamDictionaryFactory",
    "TrieDictionaryFactory",
]
