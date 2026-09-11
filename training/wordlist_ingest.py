"""Ingest a raw ``lemma<TAB>form`` wordlist (kaikki_to_tsv / wikidata_lexemes
output under training/lists/) into a language's dictionary.

The resolved list is the base (duplicate lines = evidence); for an
already-shipped language the installed mappings win every shared key, so a
re-extraction only ADDS. The result then runs through dictionary_builder's
layer/hygiene/encode pipeline like a routine rebuild.

Usage: uv run python -m training.wordlist_ingest <lang> [--gate] [--in-place]

--gate refuses to write when the ingested dictionary regresses the routine
rebuild (or identity, for a new language) on any UD train treebank.
"""

import argparse
import logging
from collections import Counter, defaultdict
from pathlib import Path

from simplemma.strategies.defaultrules import RULE_FUNCTIONS
from simplemma.strategies.dictionaries import dictionary_factory
from simplemma.utils import levenshtein_dist
from training.clean_wordlist import canonicalize, check_field
from training.dictionary_builder import (
    _canon,
    _compose_base,
    _compose_from_base,
    _is_single_token,
    _write_dictionary,
)
from training.eval_gate import gate as eval_gate, report_results

LOGGER = logging.getLogger(__name__)

LISTS_DIR = Path(__file__).parent / "lists"

# Headword identity must NOT override an attested form-of mapping here (grc
# ἀκούσας; removal measured -3.8/-7.8pp). Force-identity stays the default,
# gate-proven net-positive elsewhere (nl +17pp, bg/uk +6pp).
IDENTITY_SOFT_LANGS = frozenset({"grc"})

# Break an attestation TIE by paradigm size before Levenshtein: distance
# alone lets a rare lexeme win an ultra-frequent form (grc ἦν). Per-language,
# gated; gl/lt FAILED and the prior loses elsewhere -- never the default.
PARADIGM_PRIOR_LANGS: frozenset[str] = frozenset(
    {"cy", "el", "et", "grc", "hy", "nl", "sk", "sv"}
)


def _collect_candidates(
    path: Path, langcode: str
) -> tuple[dict[str, Counter[str]], set[str]]:
    """First pass: filter input lines, counting each (form, lemma) pair as evidence.

    Per-line diagnostics (wrong format, rule mismatch) are DEBUG-gated: the
    rule check is otherwise skipped for cost."""
    diagnose = LOGGER.isEnabledFor(logging.DEBUG)
    candidates: defaultdict[str, Counter[str]] = defaultdict(Counter)
    lemmas: set[str] = set()
    with open(path, encoding="utf-8") as filehandle:
        for line in filehandle:
            columns = [
                _canon(canonicalize(c), langcode) for c in line.strip().split("\t")
            ]
            if len(columns) != 2 or not columns[0]:
                LOGGER.debug("wrong format: %s", line.strip())
                continue
            # drop fields a tokenizer could never yield as one token, or
            # carrying mojibake/control chars.
            if any(not _is_single_token(c) or check_field(c) for c in columns):
                continue
            if len(columns[0]) == 1 and len(columns[1]) > 6:
                continue
            if len(columns[0]) > 6 and len(columns[1]) == 1:
                continue
            # diagnose rules disagreeing with the list
            if diagnose and len(columns[1]) > 6 and langcode in RULE_FUNCTIONS:
                rule = RULE_FUNCTIONS[langcode](columns[1])
                if rule and rule != columns[0]:
                    LOGGER.debug(
                        "rule mismatch: %s %s %s", columns[1], columns[0], rule
                    )
            candidates[columns[1]][columns[0]] += 1
            lemmas.add(columns[0])
    return candidates, lemmas


def _resolve_candidates(
    candidates: dict[str, Counter[str]],
    lemmas: set[str],
    langcode: str,
) -> dict[str, str]:
    """Second pass: pick one lemma per form (most attestations, then paradigm
    size for PARADIGM_PRIOR_LANGS, then distance)."""
    diagnose = LOGGER.isEnabledFor(logging.DEBUG)
    paradigm_size: Counter[str] = Counter()
    if langcode in PARADIGM_PRIOR_LANGS:
        for counts in candidates.values():
            paradigm_size.update(counts.keys())
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
                -paradigm_size[item[0]],
                levenshtein_dist(word_form, item[0]),
                item[0],
            ),
        )[0]
        if diagnose:
            LOGGER.debug(
                "diverging: %s -> %s | candidates: %s",
                word_form,
                best,
                sorted(options.items()),
            )
        mydict[word_form] = best
    # Force identity: a headword is its own lemma. Soft (setdefault only) for
    # IDENTITY_SOFT_LANGS and for lemmas attested only by their own line
    # (forcing those measured -1.3..-2.6pp).
    soft = langcode in IDENTITY_SOFT_LANGS
    strong = (
        set()
        if soft
        else {
            lemma
            for form, counts in candidates.items()
            for lemma in counts
            if lemma != form
        }
    )
    for word in lemmas:
        if word in strong:
            mydict[word] = word
        else:
            mydict.setdefault(word, word)
    return mydict


def read_wordlist(path: Path, langcode: str) -> dict[str, str]:
    """Resolve a raw ``lemma<TAB>form`` wordlist at `path` into a form->lemma dict."""
    candidates, lemmas = _collect_candidates(path, langcode)
    mydict = _resolve_candidates(candidates, lemmas, langcode)
    LOGGER.debug("%s: %d entries", langcode, len(mydict))
    return mydict


def ingest(
    langcode: str,
    listpath: str | Path = LISTS_DIR,
    filepath: str | None = None,
    in_place: bool = False,
    gate: bool = False,
) -> None:
    """Build `langcode` from `listpath`/<langcode>.txt; with `gate`, raise
    instead of writing on a UD regression."""
    listdir = Path(listpath)
    if not listdir.is_absolute():
        listdir = Path(__file__).parent / listdir
    shipped = (
        _compose_base(langcode)
        if langcode in dictionary_factory.SUPPORTED_LANGUAGES
        else None
    )
    mydict = read_wordlist(listdir / f"{langcode}.txt", langcode)
    if shipped:
        mydict.update(shipped)
    mydict = _compose_from_base(mydict, langcode)
    if gate:
        baseline = _compose_from_base(shipped, langcode) if shipped else {}
        if not report_results(eval_gate(langcode, baseline, mydict)):
            raise RuntimeError(f"{langcode}: eval gate FAILED, nothing written")
    _write_dictionary(mydict, langcode, filepath, in_place)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write into the installed package's data directory (default: training/output/).",
    )
    parser.add_argument(
        "--gate", action="store_true", help="Refuse to write on a UD regression."
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    ingest(args.lang, in_place=args.in_place, gate=args.gate)
