"""Dictionary factory protocol and the default (in-memory) backend."""

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
# frozenset: O(1) membership checks.
SUPPORTED_LANGUAGES = frozenset(f.stem for f in DATA_FOLDER.glob("*.plzma"))


def _read_decompressed(langcode: str) -> bytes:
    """Read and lzma-decompress the shipped `data/{langcode}.plzma`."""
    # single validation point; also excludes path traversal
    if langcode not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {langcode}")
    with lzma.open(DATA_FOLDER / f"{langcode}.plzma", "rb") as filehandle:
        return filehandle.read()


def _load_dictionary_from_disk(langcode: str) -> dict[bytes, bytes]:
    """Load the shipped `data/{langcode}.plzma` as a bytes->bytes dict."""
    return frontcode._decode_stream(_read_decompressed(langcode))


class DictionaryFactory(Protocol):
    """Protocol for loading form-to-lemma dictionaries by language code."""

    __slots__ = ()

    @abstractmethod
    def get_dictionary(
        self,
        lang: str,
    ) -> Mapping[str, str]:
        """Return the dictionary for `lang` (raise ValueError if unsupported)."""


class DecodedStrMapping(Mapping[str, str]):
    """Read-only str->str view over a bytes-backed store, decoding on access.

    Subclasses implement `_lookup` (None on a miss), `__iter__`, `__len__`; the
    shared `__getitem__`/`get` (miss-cheap, avoiding Mapping.get's EAFP) is here.
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
    """Base wiring an lru cache (size `cache_max_size`) around the subclass's
    `_get_dictionary_uncached`; caches the built value, not the raw data."""

    __slots__ = ("_get_dictionary",)

    def __init__(self, cache_max_size: int = 8) -> None:
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
    """Load the shipped dictionaries into plain dicts, caching up to `cache_max_size` languages."""

    __slots__ = ()

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        return MappingStrToByteString(_load_dictionary_from_disk(lang))


# Process-wide default: the strategy defaults and the legacy helpers all share
# this one instance, so the shipped dictionaries are cached once, not per site.
DEFAULT_DICTIONARY_FACTORY = DefaultDictionaryFactory()
