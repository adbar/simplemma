"""
Dictionary Factory
------------------

This file defines the `DictionaryFactory` protocol and the `DefaultDictionaryFactory` class. It provides functionality for loading and accessing dictionaries for supported languages.

Classes:
- `DictionaryFactory`: A protocol defining the interface for a dictionary factory.
- `DefaultDictionaryFactory`: A concrete implementation of the `DictionaryFactory` protocol.
"""

import lzma
import pickle
import sys
from abc import abstractmethod
from os import listdir, path
from pathlib import Path
from typing import Dict

from functools import lru_cache

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

DATA_FOLDER = str(Path(__file__).parent / "data")
SUPPORTED_LANGUAGES = [
    path.splitext(dict)[0]
    for dict in listdir(DATA_FOLDER)
    if path.isfile(path.join(DATA_FOLDER, dict)) and dict.endswith(".plzma")
]


def _load_dictionary_from_disk(langcode: str) -> Dict[str, str]:
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
    Dictionary Factory protocol.

    This protocol defines the interface for a dictionary factory, which is responsible for loading and providing access to dictionaries for different languages.

    Methods:
    - `get_dictionary(lang: str) -> Dict[str, str]`: Get the dictionary for a specific language.

    Note:
        Concrete implementations of this protocol should provide a concrete implementation for the `get_dictionary` method.
    """

    @abstractmethod
    def get_dictionary(
        self,
        lang: str,
    ) -> Dict[str, str]:
        """
        Get the dictionary for a specific language.

        Args:
            lang (str): The language code.

        Returns:
            Dict[str, str]: The dictionary for the specified language.

        Raises:
            ValueError: If the specified language is not supported.
        """
        raise NotImplementedError


class DefaultDictionaryFactory(DictionaryFactory):
    """
    Default Dictionary Factory.

    This class is a concrete implementation of the `DictionaryFactory` protocol. It provides functionality for loading and caching dictionaries from disk.

    Attributes:
    - `_data`: A dictionary to cache loaded dictionaries.
    - `_load_dictionary_from_disk`: A cached version of the `_load_dictionary_from_disk` function.

    Methods:
    - `get_dictionary(lang: str) -> Dict[str, str]`: Get the dictionary for a specific language.

    Note:
        This class assumes that the dictionary files are stored in the 'data' folder relative to this module.
    """

    __slots__ = ["_data", "_load_dictionary_from_disk"]

    def __init__(self, cache_max_size: int = 8):
        """
        Initialize the DefaultDictionaryFactory.

        Args:
            cache_max_size (int): The maximum size of the cache for loaded dictionaries.
                Defaults to `8`.
        """
        self._data: Dict[str, Dict[str, str]] = {}
        self._load_dictionary_from_disk = lru_cache(maxsize=cache_max_size)(
            _load_dictionary_from_disk
        )

    def get_dictionary(
        self,
        lang: str,
    ) -> Dict[str, str]:
        """
        Get the dictionary for a specific language.

        Args:
            lang (str): The language code.

        Returns:
            Dict[str, str]: The dictionary for the specified language.

        Raises:
            ValueError: If the specified language is not supported.
        """
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        return self._load_dictionary_from_disk(lang)
