import logging
from collections.abc import MutableMapping
from functools import lru_cache
from pathlib import Path
from typing import Any
from collections.abc import Iterator, Mapping

try:
    from marisa_trie import BytesTrie, HUGE_CACHE
    from platformdirs import user_cache_dir

    _TRIE_DEPS_AVAILABLE = True
except ImportError:
    _TRIE_DEPS_AVAILABLE = False

    class BytesTrie:  # type: ignore[no-redef]
        pass


from simplemma.__metadata__ import __version__ as SIMPLEMMA_VERSION
from simplemma.strategies.dictionaries.dictionary_factory import (
    DictionaryFactory,
    SUPPORTED_LANGUAGES,
    _load_dictionary_from_disk,
)

logger = logging.getLogger(__name__)


class TrieWrapDict(MutableMapping[str, Any]):
    """Wrapper around BytesTrie to make them behave like dicts."""

    __slots__ = ("_trie",)

    def __init__(self, trie: BytesTrie) -> None:
        self._trie = trie

    def __getitem__(self, item: str) -> Any:
        return self._trie[item][0].decode()

    def get(self, key: str, default: Any = None) -> Any:
        # Avoids MutableMapping.get's EAFP path (a KeyError raised on every miss).
        value = self._trie.get(key)
        return value[0].decode() if value else default

    def __setitem__(self, key: Any, value: Any) -> None:
        raise NotImplementedError

    def __delitem__(self, key: Any) -> None:
        raise NotImplementedError

    def __iter__(self) -> Iterator[str]:
        yield from self._trie.iterkeys()

    def __len__(self) -> int:
        return len(self._trie)


class TrieDictionaryFactory(DictionaryFactory):
    """Memory optimized DictionaryFactory backed by MARISA-tries.

    This dictionary factory creates dictionaries, which are backed by a
    MARISA-trie instead of a dict, to make them consume very little
    memory compared to the DefaultDictionaryFactory. Trade-offs are that
    lookup performance isn't as good as with dicts.
    """

    __slots__ = ["_cache_dir", "_use_disk_cache", "_get_dictionary"]

    def __init__(
        self,
        cache_max_size: int = 8,
        use_disk_cache: bool = True,
        disk_cache_dir: str | None = None,
    ) -> None:
        """Initialize the TrieDictionaryFactory.

        Args:
            cache_max_size (int): The maximum number dictionaries to
                keep in memory. Defaults to `8`.
            use_disk_cache (bool): Whether to cache the tries on disk to
                speed up loading time. Defaults to `True`.
            disk_cache_dir (str | None): Path where the generated
                tries should be stored in. Defaults to a Simplemma-
                specific subdirectory of the user's cache directory.
        """

        if not _TRIE_DEPS_AVAILABLE:
            raise ImportError(
                "marisa_trie and platformdirs are required for TrieDictionaryFactory"
            )

        if disk_cache_dir:
            self._cache_dir = Path(disk_cache_dir)
        else:
            self._cache_dir = (
                Path(user_cache_dir("simplemma")) / "marisa_trie" / SIMPLEMMA_VERSION
            )
        self._use_disk_cache = use_disk_cache
        self._get_dictionary = lru_cache(maxsize=cache_max_size)(
            self._get_dictionary_uncached
        )

    def _create_trie_from_pickled_dict(self, lang: str) -> BytesTrie:
        """Create a trie from a pickled dictionary."""
        raw = _load_dictionary_from_disk(lang)
        return BytesTrie(
            ((k.decode(), v) for k, v in raw.items()),
            cache_size=HUGE_CACHE,
        )

    def _write_trie_to_disk(self, lang: str, trie: BytesTrie) -> None:
        """Persist the trie to disk for later usage.

        The persisted trie can be loaded by subsequent runs to speed up
        loading times.
        """
        logger.debug("Caching trie on disk. This might take a second.")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        target = self._cache_dir / f"{lang}.dic"
        try:
            trie.save(target)
        except Exception:
            target.unlink(missing_ok=True)
            raise

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        """Get the dictionary for the given language."""
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")

        cache_path = self._cache_dir / f"{lang}.dic"
        if self._use_disk_cache and cache_path.exists():
            try:
                return TrieWrapDict(BytesTrie().load(cache_path))
            except Exception:
                logger.warning("Corrupt trie cache for %s, regenerating.", lang)
                cache_path.unlink(missing_ok=True)

        trie = self._create_trie_from_pickled_dict(lang)
        if self._use_disk_cache:
            try:
                self._write_trie_to_disk(lang, trie)
            except Exception:
                logger.warning("Failed to cache trie for %s on disk.", lang)
        return TrieWrapDict(trie)

    def get_dictionary(
        self,
        lang: str,
    ) -> Mapping[str, str]:
        "Retrieves a dictionary for the specified language."
        return self._get_dictionary(lang)
