"""Parts related to dictonaries."""
import lzma
import logging
import pickle

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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


def _unload_data(langdict: List[LangDict], unloading_list: Set[str]) -> List[LangDict]:
    # not especially efficient computationally speaking
    for item in [l for l in langdict if l.code in unloading_list]:
        langdict.remove(item)
    return langdict


IN_MEMORY_DICTIONARIES: List[LangDict] = []


def update_lang_data(lang: Optional[Union[str, Tuple[str]]]) -> List[LangDict]:
    # convert string
    lang = _control_lang(lang)
    global IN_MEMORY_DICTIONARIES
    if not IN_MEMORY_DICTIONARIES:
        IN_MEMORY_DICTIONARIES = _load_data(lang)
    else:
        prev_lang = tuple(l.code for l in IN_MEMORY_DICTIONARIES)
        if prev_lang != lang:
            # make lists of languages to load or unload
            # could also use set union/difference
            loading_list = tuple(l for l in lang if l not in prev_lang)
            unloading_list = set(l for l in prev_lang if l not in lang)
            # unload
            IN_MEMORY_DICTIONARIES = _unload_data(
                IN_MEMORY_DICTIONARIES, unloading_list
            )
            # load
            IN_MEMORY_DICTIONARIES.extend(_load_data(loading_list))  # type: ignore[arg-type]
        # TODO lemmatize.cache_clear()
    return IN_MEMORY_DICTIONARIES
