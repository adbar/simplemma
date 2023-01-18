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

def _load_data(langs: Optional[Tuple[str]]) -> List[LangDict]:
    """Decompress und unpickle lemmatization rules.
    Takes one or several ISO 639-1 code language code as input.
    Returns a list of dictionaries."""
    langlist = []
    assert isinstance(langs, tuple)
    for lang in langs:
        if lang not in LANGLIST:
            LOGGER.error("language not supported: %s", lang)
            continue
        LOGGER.debug("loading %s", lang)
        langlist.append(LangDict(lang, _load_pickle(lang)))
    return langlist

class DictionaryCache:
    def __init__(self):
        self.data: List[LangDict] = []

    def update_lang_data(self, lang: Optional[Union[str, Tuple[str]]]) -> Tuple[str]:
        # convert string
        lang = _control_lang(lang)
        if not self.data or tuple(l.code for l in self.data) != lang:
            self.data = _load_data(lang)
            # TODO lemmatize.cache_clear()
        return lang
