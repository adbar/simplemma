"""
Functions used to create lemmatization dictionaries out of word lists.
Input format: lemma, tab, word, newline
Output format: an lzma-compressed dict[bytes, bytes] -- a pickle by default,
or the front-coded byte stream (see frontcode.py) with --frontcode.
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
from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries import frontcode
from simplemma.strategies.dictionaries.dictionary_factory import SUPPORTED_LANGUAGES
from simplemma.utils import levenshtein_dist, normalize_token
from training.clean_wordlist import check_field, read_pairs

# Swahili inflection is prefixal, so a lemma's forms share an ENDING not a
# start; front-coding the reversed bytes exposes that shared structure.
FRONTCODE_REVERSE_KEY_LANGS = {"sw"}

# Optional per-language source layers merged by _apply_layers (precedence:
# overrides > base wordlist > fill).
OVERRIDES_DIR = Path(__file__).parent / "overrides"
FILL_DIR = Path(__file__).parent / "fill"

LOGGER = logging.getLogger(__name__)

INPUT_PUNCT = re.compile(r"[,:*/\+_]|.+-$|.+-\t|^-.+")
BUFFER_HACK = {"bg", "es", "et", "fi", "fr", "it", "lt", "pl", "sk", "uk"}  # "da", "nl"


def _determine_path(listpath: str, langcode: str) -> str:
    filename = f"{listpath}/{langcode}.txt"
    return str(Path(__file__).parent / filename)


def _collect_candidates(
    filepath: str, langcode: str, silent: bool
) -> tuple[dict[str, Counter[str]], set[str]]:
    """First pass: filter input lines, counting each (form, lemma) pair as evidence."""
    candidates: defaultdict[str, Counter[str]] = defaultdict(Counter)
    lemmas: set[str] = set()
    with open(filepath, encoding="utf-8") as filehandle:
        for line in filehandle:
            # skip potentially invalid lines, e.g. with punctuation
            if " " in line or INPUT_PUNCT.search(line):
                continue
            # NFC at the choke point: runtime lookups NFC-normalize, so keys
            # must be NFC no matter how the input list was prepared.
            columns = [normalize_token(c) for c in line.strip().split("\t")]
            # invalid: wrong shape or empty lemma
            if len(columns) != 2 or not columns[0]:
                if not silent:
                    LOGGER.warning("wrong format: %s", line.strip())
                continue
            # reject mojibake / control-char keys (clean_wordlist's guard) so
            # junk can't become a key even if that optional stage was skipped.
            if any(check_field(c) for c in columns):
                continue
            # length difference
            if len(columns[0]) == 1 and len(columns[1]) > 6:
                continue
            if len(columns[0]) > 6 and len(columns[1]) == 1:
                continue
            # print line if the rule is wrong
            if (
                len(columns[1]) > 6
                and langcode in RULE_FUNCTIONS
                and columns[1] != columns[0]
            ):
                rule = RULE_FUNCTIONS[langcode](columns[1])
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


def _layer_entries(path: Path) -> dict[bytes, bytes]:
    """A curated lemma<TAB>form layer file as a bytes form->lemma mapping.

    read_pairs enforces the shared key hygiene (NFC, no empty/junk field, no
    conflicting duplicate form) and fails loud on corruption. The one skip
    here is policy, not corruption: a multi-word form carries a space, which
    the tokenizer never yields as a single token (e.g. Wikidata lexemes like
    'top hat'), so it is an unreachable key."""
    pairs = read_pairs(path)
    entries = {
        form.encode(): lemma.encode()
        for form, lemma in pairs.items()
        if " " not in form
    }
    if len(entries) < len(pairs):
        LOGGER.info(
            "%s: skipped %d unreachable spaced forms",
            path.name,
            len(pairs) - len(entries),
        )
    return entries


def _apply_layers(base: dict[bytes, bytes], langcode: str) -> dict[bytes, bytes]:
    """Merge the optional per-language source layers into the base wordlist
    dict with explicit precedence: overrides > base > fill. Fill (e.g.
    Wikidata) never displaces a base entry; reviewed overrides always win."""
    merged = dict(base)
    fill_path = FILL_DIR / f"{langcode}.tsv"
    if fill_path.exists():
        for form, lemma in _layer_entries(fill_path).items():
            merged.setdefault(form, lemma)
        LOGGER.info("%s: fill layer applied -> %s entries", langcode, len(merged))
    override_path = OVERRIDES_DIR / f"{langcode}.tsv"
    if override_path.exists():
        merged.update(_layer_entries(override_path))
        LOGGER.info("%s: override layer applied -> %s entries", langcode, len(merged))
    return merged


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
    use_frontcode: bool = False,
) -> None:
    mydict = _apply_layers(_load_dict(langcode, listpath), langcode)
    if filepath is None:
        filepath = _determine_pickle_path(langcode, in_place)
    if use_frontcode:
        reverse_key = langcode in FRONTCODE_REVERSE_KEY_LANGS
        Path(filepath).write_bytes(frontcode.encode(mydict, reverse_key=reverse_key))
    else:
        # sort dictionary to help saving space during compression
        if langcode not in ("lt", "sw"):
            mydict = dict(sorted(mydict.items(), key=itemgetter(1)))
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
    parser.add_argument(
        "--frontcode",
        action="store_true",
        help="Write the front-coded byte-stream format instead of a pickle "
        "(smaller on disk, requires a simplemma release that can read it).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    for listcode in sorted(SUPPORTED_LANGUAGES):
        _pickle_dict(listcode, in_place=args.in_place, use_frontcode=args.frontcode)
