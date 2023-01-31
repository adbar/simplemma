import lzma
import logging
import pickle
import re

from pathlib import Path
from typing import Dict, List, Optional

from .constants import LANGLIST
from .utils import levenshtein_dist

try:
    from .rules import apply_rules
# local error, also ModuleNotFoundError for Python >= 3.6
except ImportError:  # pragma: no cover
    from rules import apply_rules  # type: ignore

LOGGER = logging.getLogger(__name__)

INPUT_PUNCT = re.compile(r"[,:*/\+_]|^-|-\t")
SAFE_LIMIT = {
    "cs",
    "da",
    "el",
    "en",
    "es",
    "fi",
    "fr",
    "ga",
    "hu",
    "it",
    "pl",
    "pt",
    "ru",
    "sk",
    "tr",
}

VOC_LIMIT = {"fi", "la", "pl", "pt", "sk", "tr"}
BUFFER_HACK = {"bg", "es", "et", "fi", "fr", "it", "lt", "pl", "sk", "uk"}  # "da", "nl"

MAXLENGTH = 16


def _determine_path(listpath: str, langcode: str) -> str:
    filename = f"{listpath}/{langcode}.txt"
    return str(Path(__file__).parent / filename)


def _read_dict(filepath: str, langcode: str, silent: bool) -> Dict[str, str]:
    mydict, myadditions, i = {}, [], 0  # type: Dict[str, str], List[str], int
    leftlimit = 1 if langcode in SAFE_LIMIT else 2
    # load data from list
    with open(filepath, "r", encoding="utf-8") as filehandle:
        for line in filehandle:
            # skip potentially invalid lines, e.g. with punctuation
            if " " in line or INPUT_PUNCT.search(line):
                continue
            columns = line.strip().split("\t")
            # invalid: remove noise
            if len(columns) != 2 or len(columns[0]) < leftlimit:
                # or len(columns[1]) < 2:
                if not silent:
                    LOGGER.warning("wrong format: %s", line.strip())
                continue
            # too long
            if langcode in VOC_LIMIT and (
                len(columns[0]) > MAXLENGTH or len(columns[1]) > MAXLENGTH
            ):
                continue
            # length difference
            if len(columns[0]) == 1 and len(columns[1]) > 6:
                continue
            if len(columns[0]) > 6 and len(columns[1]) == 1:
                continue
            # tackled by rules
            if len(columns[1]) > 6:  # columns[1] != columns[0]
                rule = apply_rules(columns[1], langcode)
                if rule == columns[0]:
                    continue
                if rule is not None and rule != columns[1]:
                    print(columns[1], columns[0], rule)
            # process
            if columns[1] in mydict and mydict[columns[1]] != columns[0]:
                # prevent mistakes and noise coming from the lists
                dist1, dist2 = levenshtein_dist(
                    columns[1], mydict[columns[1]]
                ), levenshtein_dist(columns[1], columns[0])
                # fail-safe: delete potential false entry
                # if dist1 >= len(columns[1]) and dist2 >= len(columns[1]):
                #    del mydict[columns[1]]
                #    continue
                if dist1 == 0 or dist2 < dist1:  # dist1 < 2
                    mydict[columns[1]] = columns[0]
                elif not silent:
                    LOGGER.warning(
                        "diverging: %s %s | %s %s",
                        columns[1],
                        mydict[columns[1]],
                        columns[1],
                        columns[0],
                    )
                    LOGGER.debug("distances: %s %s", dist1, dist2)
            else:
                mydict[columns[1]] = columns[0]
                # deal with verbal forms (mostly)
                if langcode in BUFFER_HACK:
                    myadditions.append(columns[0])
                elif columns[0] not in mydict:
                    mydict[columns[0]] = columns[0]
                i += 1
    # overwrite
    for word in myadditions:
        mydict[word] = word
    LOGGER.debug("%s %s", langcode, i)
    return dict(sorted(mydict.items()))


def _load_dict(
    langcode: str, listpath: str = "lists", silent: bool = True
) -> Dict[str, str]:
    filepath = _determine_path(listpath, langcode)
    return _read_dict(filepath, langcode, silent)


def _pickle_dict(
    langcode: str, listpath: str = "lists", filepath: Optional[str] = None
) -> None:
    mydict = _load_dict(langcode, listpath)
    # sort dictionary to help saving space during compression
    mydict = {k: v for k, v in sorted(mydict.items(), key=lambda item: item[1])}
    if filepath is None:
        filename = f"data/{langcode}.plzma"
        filepath = str(Path(__file__).parent / filename)
    with lzma.open(filepath, "wb") as filehandle:  # , filters=my_filters, preset=9
        pickle.dump(mydict, filehandle, protocol=4)
    LOGGER.debug("%s %s", langcode, len(mydict))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    for listcode in LANGLIST:
        _pickle_dict(listcode)
