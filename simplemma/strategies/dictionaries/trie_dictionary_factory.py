from functools import lru_cache
from pathlib import Path
import tempfile
from typing import ByteString, Dict, Mapping, Optional

from marisa_trie import RecordTrie, HUGE_CACHE  # type: ignore[import-not-found]

from simplemma import __version__ as SIMPLEMMA_VERSION
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    DictionaryFactory,
    DefaultDictionaryFactory,
)


class TrieWrapDict(Mapping[str, str]):
    """Wrapper around RecordTrie to make them behave like dicts."""

    __slots__ = ["_trie"]

    def __init__(self, trie: RecordTrie):
        self._trie = trie

    def __getitem__(self, item: str) -> str:
        return self._trie[item][0]

    def __iter__(self):
        for key in self._trie.iterkeys():
            yield key

    def __len__(self):
        return len(self._trie)


class TrieDictionaryFactory(DictionaryFactory):
    """Memory optimized DictionaryFactory backed by MARISA-tries.

    This dictionary factory creates dictionaries, which are backed by a
    MARISA-trie instead of a dict, to make them consume very little
    memory compared to the DefaultDictionaryFactory. Trade-offs are that
    lookup performance isn't as good as with dicts.
    """

    __slots__ = ["_cache_dir", "_defaultDictionaryFactory", "_get_dictionary"]

    def __init__(
        self,
        cache_max_size: int = 8,
        use_disk_cache: bool = True,
        disk_cache_dir: Optional[str] = None,
    ) -> None:
        """Initialize the TrieDictionaryFactory.

        Args:
            cache_max_size (int): The maximum number dictionaries to
                keep in memory. Defaults to `8`.
            use_disk_cache (bool): Whether to cache the tries on disk to
                speed up loading time. Defaults to `True`.
            disk_cache_dir (Optional[str]): Path where the generated
                tries should be stored in. Defaults to a Simplemma-
                specific subdirectory of the user's cache directory.
        """

        self._defaultDictionaryFactory = DefaultDictionaryFactory(cache_max_size=0)
        if use_disk_cache:
            self._cache_dir: Optional[Path] = (
                Path(disk_cache_dir)
                if disk_cache_dir is not None
                else (Path(tempfile.gettempdir()) / "simplemma" / SIMPLEMMA_VERSION)
            )
        else:
            self._cache_dir = None

        self._get_dictionary = lru_cache(maxsize=cache_max_size)(
            self._get_dictionary_uncached
        )

    def _try_read_trie_from_disk(self, lang: str) -> bool:
        """Check if a trie for the given language is available on disk."""
        if self._cache_dir is None:
            return False
        try:
            return RecordTrie().load(str(self._cache_dir / f"{lang}.pkl"))
        except FileNotFoundError:
            return False

    def _write_trie_to_disk(self, lang: str, trie: RecordTrie) -> None:
        """Persist the trie to disk for later usage.

        The persisted trie can be loaded by subsequent runs to speed up
        loading times.
        """
        if self._cache_dir is None:
            return

        trie.save(self._cache_dir / f"{lang}.pkl")

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        """Get the dictionary for the given language."""
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")

        if self._cache_dir:
            trie = RecordTrie().load(str(self._cache_dir / f"{lang}.pkl"))

        if trie is None:
            trie = RecordTrie(
                self._defaultDictionaryFactory.get_dictionary(lang).items(),
                cache_size=HUGE_CACHE,
            )
            if self._cache_dir:
                self._write_trie_to_disk(lang, trie)

        return TrieWrapDict(trie)

    def get_dictionary(
        self,
        lang: str,
    ) -> Mapping[str, str]:
        return self._get_dictionary(lang)
