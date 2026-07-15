"""
Functions used to create lemmatization dictionaries out of word lists.
Input format: lemma, tab, word, newline
Output format: the front-coded, lzma-compressed byte stream (see frontcode.py)
that the runtime loads. Written to .plzma; `frontcode.load` also still reads
the legacy pickled dicts shipped before v2.0.
"""

import argparse
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries import frontcode
from simplemma.strategies.dictionaries.dictionary_factory import (
    DATA_FOLDER,
    SUPPORTED_LANGUAGES,
    _load_dictionary_from_disk,
)
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
            # diagnose rules disagreeing with the list (skipped when silent)
            if (
                not silent
                and len(columns[1]) > 6
                and langcode in RULE_FUNCTIONS
                and columns[1] != columns[0]
            ):
                rule = RULE_FUNCTIONS[langcode](columns[1])
                if rule and rule != columns[0]:
                    LOGGER.warning(
                        "rule mismatch: %s %s %s", columns[1], columns[0], rule
                    )
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
    # convert to bytestrings; no need to sort, frontcode.encode sorts by key
    return {k.encode("utf-8"): v.encode("utf-8") for k, v in mydict.items()}


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


def _determine_output_path(langcode: str = "en", in_place: bool = False) -> str:
    """in_place=True overwrites shipped data; default writes to training/output/."""
    filename = f"{langcode}.plzma"
    if in_place:
        directory = DATA_FOLDER  # where the runtime loads from
    else:
        directory = Path(__file__).parent / "output"
        directory.mkdir(parents=True, exist_ok=True)
    return str(directory / filename)


def _build_dictionary(
    langcode: str = "en",
    listpath: str = "lists",
    filepath: str | None = None,
    in_place: bool = False,
    from_shipped: bool = False,
) -> None:
    # from_shipped: Phase-5a reship base = the already-built shipped dict decoded
    # verbatim (NOT re-run through _read_dict's filters), so only the override/
    # fill layers change content. Otherwise rebuild the base from the wordlists.
    base = (
        _load_dictionary_from_disk(langcode)
        if from_shipped
        else _load_dict(langcode, listpath)
    )
    mydict = _apply_layers(base, langcode)
    if filepath is None:
        filepath = _determine_output_path(langcode, in_place)
    reverse_key = langcode in FRONTCODE_REVERSE_KEY_LANGS
    Path(filepath).write_bytes(frontcode.encode(mydict, reverse_key=reverse_key))
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
        "--from-shipped",
        action="store_true",
        help="Phase-5a reship: compose from the shipped dict + override/fill "
        "layers instead of rebuilding the base from wordlists.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    for listcode in sorted(SUPPORTED_LANGUAGES):
        _build_dictionary(
            listcode,
            in_place=args.in_place,
            from_shipped=args.from_shipped,
        )
