"""DictionaryFactory module. A DictionaryFactory is a class that provides dictionary data."""

import lzma
import logging
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

LOGGER = logging.getLogger(__name__)


DATA_FOLDER = str(Path(__file__).parent / "data")
SUPPORTED_LANGUAGES = [
    path.splitext(dict)[0]
    for dict in listdir(DATA_FOLDER)
    if path.isfile(path.join(DATA_FOLDER, dict)) and dict.endswith(".plzma")
]


def _load_dictionary_from_disk(langcode: str) -> Dict[str, str]:
    filename = f"data/{langcode}.plzma"
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, "rb") as filehandle:
        pickled_dict = pickle.load(filehandle)
        assert isinstance(pickled_dict, dict)
        return pickled_dict


class DictionaryFactory(Protocol):
    @abstractmethod
    def get_dictionary(
        self,
        lang: str,
    ) -> Dict[str, str]:
        raise NotImplementedError


class DefaultDictionaryFactory(DictionaryFactory):
    __slots__ = ["_data", "_load_dictionary_from_disk"]

    def __init__(self, cache_max_size: int = 8):
        self._data: Dict[str, Dict[str, str]] = {}
        self._load_dictionary_from_disk = lru_cache(maxsize=cache_max_size)(
            _load_dictionary_from_disk
        )

    def get_dictionary(
        self,
        lang: str,
    ) -> Dict[str, str]:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {lang}")
        LOGGER.debug("loading %s", lang)
        return self._load_dictionary_from_disk(lang)
