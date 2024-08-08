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
from os import listdir, path
from pathlib import Path
from typing import ByteString, Dict, Iterator, Mapping, Protocol

DATA_FOLDER = str(Path(__file__).parent / "data")
SUPPORTED_LANGUAGES = [
    path.splitext(dict)[0]
    for dict in listdir(DATA_FOLDER)
    if path.isfile(path.join(DATA_FOLDER, dict)) and dict.endswith(".plzma")
]


def _load_dictionary_from_disk(langcode: str) -> Dict[ByteString, ByteString]:
    """
    Load a dictionary from disk.

    Args:
        langcode (str): The language code.

    Returns:
        Dict[str, str]: The loaded dictionary.

    Raises:
        AssertionError: If the loaded object is not a dictionary.

    Note:
        This function assumes that the dictionary file is stored in the 'data' folder relative to this module.
        The file name is constructed by appending '.plzma' to the language code.
    """
    filename = f"data/{langcode}.plzma"
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, "rb") as filehandle:
        pickled_dict = pickle.load(filehandle)
        assert isinstance(pickled_dict, dict)
        return pickled_dict


class DictionaryFactory(Protocol):
    """
    This protocol defines the interface for a dictionary factory, which is responsible for loading and providing access to dictionaries for different languages.

    Note:
        This protocol should be implemented by concrete dictionary factories.
        Concrete implementations of this protocol should provide a concrete implementation for the `get_dictionary` method.
    """

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

    def __init__(self, dictionary: Dict[bytes, bytes]) -> None:
        self._dict = dictionary

    def __getitem__(self, item: str) -> str:
        return self._dict[item.encode()].decode()

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

    __slots__ = ["_load_dictionary_from_disk"]

    def __init__(self, cache_max_size: int = 8) -> None:
        """
        Initialize the DefaultDictionaryFactory.

        Args:
            cache_max_size (int): The maximum size of the cache for loaded dictionaries.
                Defaults to `8`.
        """
        self._load_dictionary_from_disk = lru_cache(maxsize=cache_max_size)(
            _load_dictionary_from_disk
        )

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
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return MappingStrToByteString(self._load_dictionary_from_disk(lang))
