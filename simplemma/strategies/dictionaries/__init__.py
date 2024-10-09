"""Dictionary-based lemmatization strategy."""

from .dictionary_factory import DefaultDictionaryFactory, DictionaryFactory
from .trie_directory_factory import TrieDictionaryFactory

__all__ = ["DefaultDictionaryFactory", "DictionaryFactory", "TrieDictionaryFactory"]
