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
    """The most memory-efficient available backend: `TrieDictionaryFactory` if
    `marisa_trie` is installed, else the stdlib `StreamDictionaryFactory`.

    The trie backend spikes to full-dict memory on first use and caches to
    disk; the stream backend does neither.
    """
    try:
        return TrieDictionaryFactory()
    except ImportError:
        return StreamDictionaryFactory()


# Process-wide default for the `low_memory=` flag, mirroring
# DEFAULT_DICTIONARY_FACTORY: without this, each low_memory call site would
# build its own backend and load its own copy of every language's dictionary.
# Imported by lemmatizer.py and default.py; listed in __all__ so it reads as
# an intentional (package-internal) export rather than an unused global.
_shared_low_memory_factory = lru_cache(maxsize=None)(make_low_memory_factory)


__all__ = [
    "DEFAULT_DICTIONARY_FACTORY",
    "DefaultDictionaryFactory",
    "DictionaryFactory",
    "StreamDictionaryFactory",
    "TrieDictionaryFactory",
    "make_low_memory_factory",
    "_shared_low_memory_factory",
]
