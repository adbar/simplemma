"""Dictionary-based lemmatization strategy."""

from .dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultDictionaryFactory,
    DictionaryFactory,
)
from .trie_dictionary_factory import TrieDictionaryFactory

__all__ = [
    "DEFAULT_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "TrieDictionaryFactory",
]
