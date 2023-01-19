"""Parts related to dictonaries."""
import lzma
import logging
import pickle

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .constants import LANGLIST

LOGGER = logging.getLogger(__name__)


class LangDict:
    "Class to store word pairs and relevant information for a single language."
    __slots__ = ("code", "dict")

    def __init__(self, langcode: str, langdict: Dict[str, str]):
        self.code: str = langcode
        self.dict: Dict[str, str] = langdict


def _control_lang(lang: Any) -> Tuple[str]:
    "Make sure the lang variable is a valid tuple."
    # convert string
    if isinstance(lang, str):
        lang = (lang,)
    if not isinstance(lang, tuple):
        raise TypeError("lang argument must be a two-letter language code")
    return lang  # type: ignore[return-value]


def _load_pickle(langcode: str) -> Dict[str, str]:
    filename = f"data/{langcode}.plzma"
    filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, "rb") as filehandle:
        pickled_dict = pickle.load(filehandle)
        assert isinstance(pickled_dict, dict)
        return pickled_dict


class DictionaryCache:
    def __init__(self, cache_max_size: int = 5):
        self.data: List[LangDict] = []
        self._load_pickle = lru_cache(maxsize=cache_max_size)(_load_pickle)

    def update_lang_data(self, langs: Optional[Union[str, Tuple[str]]]) -> Tuple[str]:
        # convert string
        langs = _control_lang(langs)
        if self.data and tuple(l.code for l in self.data) == langs:
            return langs

        self.data = []
        assert isinstance(langs, tuple)
        for lang in langs:
            if lang not in LANGLIST:
                LOGGER.error("language not supported: %s", lang)
                continue
            LOGGER.debug("loading %s", lang)
            self.data.append(LangDict(lang, self._load_pickle(lang)))
        return langs
