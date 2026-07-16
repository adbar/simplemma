"""
This module defines the `DictionaryFactory` protocol and the `DefaultDictionaryFactory` class.
It provides functionality for loading and accessing dictionaries for supported languages.

- [DictionaryFactory][simplemma.strategies.dictionaries.DictionaryFactory]: The Protocol class for all dictionary factories.
- [DefaultDictionaryFactory][simplemma.strategies.dictionaries.DefaultDictionaryFactory]: Default dictionary factory.
It loads the dictionaries that are shipped with simplemma and caches them as configured.

"""

from abc import abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Protocol, TypeVar, overload
from collections.abc import Iterator, Mapping

try:
    import lzma
except ImportError as error:
    raise ImportError(
        "simplemma's dictionaries are lzma-compressed, but the 'lzma' module "
        "is unavailable. This usually means Python was built without "
        "liblzma support (common on from-source builds missing the "
        "liblzma-dev/xz headers at compile time). Reinstall Python with "
        "liblzma development headers present, then rebuild."
    ) from error

from . import frontcode

_T = TypeVar("_T")

DATA_FOLDER = Path(__file__).parent / "data"
# frozenset: O(1) membership, checked on every get_dictionary call.
SUPPORTED_LANGUAGES = frozenset(f.stem for f in DATA_FOLDER.glob("*.plzma"))


def _load_dictionary_from_disk(langcode: str) -> dict[bytes, bytes]:
    """Load the shipped `data/{langcode}.plzma` as a bytes->bytes dict."""
    filepath = DATA_FOLDER / f"{langcode}.plzma"
    with lzma.open(filepath, "rb") as filehandle:
        return frontcode.load(filehandle)


class DictionaryFactory(Protocol):
    """
    This protocol defines the interface for a dictionary factory, which is responsible for loading and providing access to dictionaries for different languages.

    Note:
        This protocol should be implemented by concrete dictionary factories.
        Concrete implementations of this protocol should provide a concrete implementation for the `get_dictionary` method.
    """

    __slots__ = ()

    @abstractmethod
    def get_dictionary(
        self,
        lang: str,
    ) -> Mapping[str, str]:
        """
        Get the dictionary for a specific language.

        Args:
            lang (str): The language code.

        Returns:
            Mapping[str, str]: The dictionary for the specified language.

        Raises:
            ValueError: If the specified language is not supported.
        """
        raise NotImplementedError


class DecodedStrMapping(Mapping[str, str]):
    """Read-only str->str view over a bytes-backed store, decoding on access.

    Subclasses implement `_lookup` (None on a miss) plus `__iter__`/`__len__`;
    the shared `__getitem__`/`get` machinery -- including the strict-mypy
    overloads and the miss-cheap `get` that avoids Mapping.get's
    KeyError-per-miss EAFP path -- lives here once.
    """

    __slots__ = ()

    @abstractmethod
    def _lookup(self, key: str) -> str | None:
        """The decoded value for `key`, or None if absent."""
        raise NotImplementedError

    def __getitem__(self, key: str) -> str:
        value = self._lookup(key)
        if value is None:
            raise KeyError(key)
        return value

    @overload
    def get(self, key: str) -> str | None: ...
    @overload
    def get(self, key: str, default: str | _T) -> str | _T: ...
    def get(self, key: str, default: str | _T | None = None) -> str | _T | None:
        value = self._lookup(key)
        return value if value is not None else default


class MappingStrToByteString(DecodedStrMapping):
    """Wrapper around a bytes->bytes dict to make it behave like a str dict."""

    __slots__ = ("_dict",)

    def __init__(self, dictionary: dict[bytes, bytes]) -> None:
        self._dict = dictionary

    def _lookup(self, key: str) -> str | None:
        value = self._dict.get(key.encode())
        return value.decode() if value is not None else None

    def __iter__(self) -> Iterator[str]:
        for key in self._dict:
            yield key.decode()

    def __len__(self) -> int:
        return len(self._dict)


class CachingDictionaryFactory(DictionaryFactory):
    """Base for factories that build a per-language dictionary once and cache it.

    `__init__` wires an lru cache around `_get_dictionary_uncached` (which
    subclasses implement); `get_dictionary` serves from it. Caching the built
    value, not the raw data, avoids rebuilding on every call and lets the lru
    bound memory by evicting whole entries together.
    """

    __slots__ = ("_get_dictionary",)

    def __init__(self, cache_max_size: int = 8) -> None:
        """
        Args:
            cache_max_size (int): The maximum number of dictionaries to keep in
                memory. Defaults to `8`.
        """
        self._get_dictionary = lru_cache(maxsize=cache_max_size)(
            self._get_dictionary_uncached
        )

    @abstractmethod
    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        """Build the dictionary for `lang` without caching (raise ValueError if
        the language is unsupported)."""
        raise NotImplementedError

    def get_dictionary(
        self,
        lang: str,
    ) -> Mapping[str, str]:
        """The cached dictionary for `lang` (see the `DictionaryFactory` protocol)."""
        return self._get_dictionary(lang)


class DefaultDictionaryFactory(CachingDictionaryFactory):
    """
    Default Dictionary Factory.

    This class is a concrete implementation of the `DictionaryFactory` protocol.
    It provides functionality for loading and caching dictionaries from disk that are included in Simplemma.
    """

    __slots__ = ()

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return MappingStrToByteString(_load_dictionary_from_disk(lang))


# Process-wide default: the strategy defaults and the legacy helpers all share
# this one instance, so the shipped dictionaries are cached once, not per site.
DEFAULT_DICTIONARY_FACTORY = DefaultDictionaryFactory()
