"""Dictionary-based lemmatization strategy."""

from .dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultDictionaryFactory,
    DictionaryFactory,
)
from .stream_dictionary_factory import StreamDictionaryFactory
from .trie_dictionary_factory import TrieDictionaryFactory


def make_low_memory_factory() -> DictionaryFactory:
    """The most memory-efficient available backend: `TrieDictionaryFactory` if
    `marisa_trie` is installed, else the stdlib `StreamDictionaryFactory`.

    The trie backend spikes to full-dict memory on first use and caches to
    disk; the stream backend does neither.
    """
    try:
        return TrieDictionaryFactory()
    except ImportError:
        return StreamDictionaryFactory()


__all__ = [
    "DEFAULT_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "StreamDictionaryFactory",
    "TrieDictionaryFactory",
    "make_low_memory_factory",
]
