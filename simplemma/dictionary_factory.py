"""Parts related to dictonaries."""
import lzma
import logging
import pickle

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .constants import LANGLIST

LOGGER = logging.getLogger(__name__)


def _validate_and_normalize_langs(
    langs: Optional[Union[str, Tuple[str]]]
) -> Tuple[str]:
    "Make sure the lang variable is a valid tuple."
    # convert string
    if isinstance(langs, str):
        langs = (langs,)

    if not isinstance(langs, tuple):
        raise TypeError("lang argument must be a two-letter language code")

    valid_langs = []
    for lang in langs:
        if lang not in LANGLIST:
            LOGGER.error("language not supported: %s", lang)
        else:
            valid_langs.append(lang)
    return tuple(valid_langs)  # type: ignore[return-value]


def _load_dictionary_from_disk(langcode: str) -> Dict[str, str]:
    filename = f"data/{langcode}.plzma"
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, "rb") as filehandle:
        pickled_dict = pickle.load(filehandle)
        assert isinstance(pickled_dict, dict)
        return pickled_dict


class DictionaryFactory:
    def __init__(self, cache_max_size: int = 1048576):
        self.data: Dict[str, dict] = {}
        self._load_dictionary_from_disk = lru_cache(maxsize=cache_max_size)(
            _load_dictionary_from_disk
        )

    def get_dictionaries(
        self, langs: Optional[Union[str, Tuple[str]]]
    ) -> Dict[str, dict]:
        langs = _validate_and_normalize_langs(langs)

        if self.data and tuple(sorted(self.data.keys())) == sorted(langs):
            return self.data

        self.data = {}
        for lang in langs:
            LOGGER.debug("loading %s", lang)
            self.data[lang] = self._load_dictionary_from_disk(lang)
        return self.data
