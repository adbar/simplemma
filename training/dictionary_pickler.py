"""
Functions used to created lemmatization dictionaries out of word lists.
Input format: lemma, tab, word, newline
Output format: pickled Python dictionary compressed with lzma.
"""

import argparse
import logging
import lzma
import pickle
import re
from collections import Counter, defaultdict
from operator import itemgetter
from pathlib import Path

import simplemma
from simplemma.strategies.defaultrules import DEFAULT_RULES
from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES
from simplemma.utils import levenshtein_dist

LOGGER = logging.getLogger(__name__)

INPUT_PUNCT = re.compile(r"[,:*/\+_]|.+-$|.+-\t|^-.+")
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
    "lv",
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


def _collect_candidates(
    filepath: str, langcode: str, silent: bool
) -> tuple[dict[str, Counter[str]], set[str]]:
    """First pass: filter input lines, counting each (form, lemma) pair as evidence."""
    candidates: defaultdict[str, Counter[str]] = defaultdict(Counter)
    lemmas: set[str] = set()
    leftlimit = 1 if langcode in SAFE_LIMIT else 2
    with open(filepath, encoding="utf-8") as filehandle:
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
            # print line if the rule is wrong
            if (
                len(columns[1]) > 6
                and langcode in DEFAULT_RULES
                and columns[1] != columns[0]
            ):
                rule = DEFAULT_RULES[langcode](columns[1])
                if rule and rule != columns[0]:
                    print(columns[1], columns[0], rule)
            candidates[columns[1]][columns[0]] += 1
            lemmas.add(columns[0])
    return candidates, lemmas


def _resolve_candidates(
    candidates: dict[str, Counter[str]],
    lemmas: set[str],
    langcode: str,
    silent: bool,
) -> dict[bytes, bytes]:
    """Second pass: pick one lemma per form (most attestations, then distance)."""
    mydict: dict[str, str] = {}
    for word_form, counts in candidates.items():
        options = dict(counts)
        if word_form in lemmas:
            options.setdefault(word_form, 0)
        if len(options) == 1:
            mydict[word_form] = next(iter(options))
            continue
        best = min(
            options.items(),
            key=lambda item: (
                -item[1],
                levenshtein_dist(word_form, item[0]),
                item[0],
            ),
        )[0]
        if not silent:
            LOGGER.warning(
                "diverging: %s -> %s | candidates: %s",
                word_form,
                best,
                sorted(options.items()),
            )
        mydict[word_form] = best
    # lemma identities (deal with verbal forms, mostly)
    if langcode in BUFFER_HACK:
        for word in lemmas:
            mydict[word] = word
    else:
        for word in lemmas:
            mydict.setdefault(word, word)
    LOGGER.debug("%s %s", langcode, len(mydict))
    # sort and convert to bytestrings
    return {k.encode("utf-8"): v.encode("utf-8") for k, v in sorted(mydict.items())}


def _read_dict(filepath: str, langcode: str, silent: bool) -> dict[bytes, bytes]:
    candidates, lemmas = _collect_candidates(filepath, langcode, silent)
    return _resolve_candidates(candidates, lemmas, langcode, silent)


def _load_dict(
    langcode: str, listpath: str = "lists", silent: bool = True
) -> dict[bytes, bytes]:
    filepath = _determine_path(listpath, langcode)
    return _read_dict(filepath, langcode, silent)


def _determine_pickle_path(langcode: str = "en", in_place: bool = False) -> str:
    """in_place=True overwrites shipped data; default writes to training/output/."""
    filename = f"{langcode}.plzma"
    if in_place:
        directory = Path(simplemma.__file__).parent / "strategies/dictionaries/data"
    else:
        directory = Path(__file__).parent / "output"
        directory.mkdir(parents=True, exist_ok=True)
    return str(directory / filename)


def _pickle_dict(
    langcode: str = "en",
    listpath: str = "lists",
    filepath: str | None = None,
    in_place: bool = False,
) -> None:
    mydict = _load_dict(langcode, listpath)
    # sort dictionary to help saving space during compression
    if langcode not in ("lt", "sw"):
        mydict = dict(sorted(mydict.items(), key=itemgetter(1)))
    if filepath is None:
        filepath = _determine_pickle_path(langcode, in_place)
    with lzma.open(filepath, "wb") as filehandle:  # , filters=my_filters, preset=9
        pickle.dump(mydict, filehandle, protocol=5)
    LOGGER.debug("%s %s", langcode, len(mydict))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write into the installed simplemma package's data directory, "
        "overwriting shipped dictionaries. Without this flag, output goes "
        "to training/output/ instead.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    for listcode in sorted(SUPPORTED_LANGUAGES):
        _pickle_dict(listcode, in_place=args.in_place)
