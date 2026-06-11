"""
This module defines the `DictionaryFactory` protocol and the `DefaultDictionaryFactory` class.
It provides functionality for loading and accessing dictionaries for supported languages.

- [DictionaryFactory][simplemma.strategies.dictionaries.DictionaryFactory]: The Protocol class for all dictionary factories.
- [DefaultDictionaryFactory][simplemma.strategies.dictionaries.DefaultDictionaryFactory]: Default dictionary factory.
It loads the dictionaries that are shipped with simplemma and caches them as configured.

"""

import lzma
import pickle
from abc import abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Protocol, TypeVar, overload
from collections.abc import Iterator, Mapping

_T = TypeVar("_T")

DATA_FOLDER = Path(__file__).parent / "data"
# frozenset: O(1) membership, checked on every get_dictionary call.
SUPPORTED_LANGUAGES = frozenset(f.stem for f in DATA_FOLDER.glob("*.plzma"))


def _load_dictionary_from_disk(langcode: str) -> dict[bytes, bytes]:
    """
    Load a dictionary from disk.

    Args:
        langcode (str): The language code.

    Returns:
        dict[str, str]: The loaded dictionary.

    Raises:
        AssertionError: If the loaded object is not a dictionary.

    Note:
        This function assumes that the dictionary file is stored in the 'data' folder relative to this module.
        The file name is constructed by appending '.plzma' to the language code.
    """
    filepath = DATA_FOLDER / f"{langcode}.plzma"
    with lzma.open(filepath, "rb") as filehandle:
        pickled_dict = pickle.load(filehandle)
        if not isinstance(pickled_dict, dict):
            raise TypeError(f"unexpected data in {filepath}: {type(pickled_dict)}")
        return pickled_dict


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


class MappingStrToByteString(Mapping[str, str]):
    """Wrapper around ByString dict to make them behave like str dict."""

    __slots__ = ["_dict"]

    def __init__(self, dictionary: dict[bytes, bytes]) -> None:
        self._dict = dictionary

    def __getitem__(self, item: str) -> str:
        return self._dict[item.encode()].decode()

    # The overloads mirror Mapping.get's signature for strict mypy.
    @overload
    def get(self, key: str) -> str | None: ...
    @overload
    def get(self, key: str, default: str | _T) -> str | _T: ...
    def get(self, key: str, default: str | _T | None = None) -> str | _T | None:
        # Avoids Mapping.get's EAFP path (a KeyError raised on every miss).
        value = self._dict.get(key.encode())
        return value.decode() if value is not None else default

    def __iter__(self) -> Iterator[str]:
        for key in self._dict:
            yield key.decode()

    def __len__(self) -> int:
        return len(self._dict)


class DefaultDictionaryFactory(DictionaryFactory):
    """
    Default Dictionary Factory.

    This class is a concrete implementation of the `DictionaryFactory` protocol.
    It provides functionality for loading and caching dictionaries from disk that are included in Simplemma.
    """

    __slots__ = ["_get_dictionary"]

    def __init__(self, cache_max_size: int = 8) -> None:
        """
        Initialize the DefaultDictionaryFactory.

        Args:
            cache_max_size (int): The maximum size of the cache for loaded dictionaries.
                Defaults to `8`.
        """
        # Cache the wrapper, not the raw dict, to avoid re-wrapping on every
        # call; the lru evicts wrapper and dict together, bounding memory.
        self._get_dictionary = lru_cache(maxsize=cache_max_size)(
            self._get_dictionary_uncached
        )

    def _get_dictionary_uncached(self, lang: str) -> Mapping[str, str]:
        """Build the dictionary for a language, without caching."""
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return MappingStrToByteString(_load_dictionary_from_disk(lang))

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
        return self._get_dictionary(lang)
