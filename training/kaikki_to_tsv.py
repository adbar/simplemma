"""
Convert a kaikki.org JSONL Wiktionary dump into a lemma-form TSV word list
suitable as input for `dictionary_builder.py` (see training/README.rst for
the full data-preparation pipeline this script is one step of).

Input format: one JSON object per line, as downloaded from kaikki.org.
Output format: lemma, tab, word form, newline.
"""

import argparse
import json
import logging
import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from training.clean_wordlist import write_pairs

log = logging.getLogger(__name__)

# Tags marking rows that are never real inflected forms.
_UNCONDITIONAL_DROP_TAGS = frozenset(
    {
        "table-tags",
        "inflection-template",
        "class",
        "romanization",
        "transliteration",
        # tl Baybayin display-variant rows; verified inert on every other dump.
        "Baybayin",
    }
)

# Cross-reference rows (e.g. a pronoun's page listing other pronouns);
# dropped only when the form differs from the entry's own word, so a
# genuine self-mapping keeps its vote in dictionary_builder's resolution.
_CROSS_REFERENCE_TAGS = frozenset({"pronoun", "possessive", "auxiliary"})


# error-unrecognized-form is NOT a reliable junk signal: a 27-lang audit
# found it on real forms (cy mutation, ga prothesis). On tl verb pages it
# marks header-cell junk, worth +1pp+ -- dropped there only ("sole tag"
# variant measured WORSE).
_DROP_UNRECOGNIZED_FORM_LANGS = frozenset({"tl"})

_PLACEHOLDER_FORM = "-"  # marks a form that doesn't exist for this word

# Only the combining grave/acute (Cyrillic stress marking); NOT decomposition,
# which would expose precomposed Latin/Greek accents to stripping too.
_STRESS_MARKS_TABLE = str.maketrans("", "", "̀́")


def _strip_stress_marks(text: str) -> str:
    # NFC first: precomposes Greek/Latin accents (kept) so only genuinely
    # combining stress marks are dropped, whatever form the dump arrives in.
    return unicodedata.normalize("NFC", text).translate(_STRESS_MARKS_TABLE)


# Languages whose Wiktionary forms carry pedagogical vowel-LENGTH marks
# (macron/breve) that normal orthography and UD omit -- 67% of grc forms, 0% in
# UD grc. NOT global: macron is orthographic in e.g. Latvian (garā), so folding
# it there would corrupt real words.
_LENGTH_MARK_LANGS = {"grc"}
_LENGTH_MARKS_TABLE = str.maketrans("", "", "̄̆")  # combining macron, breve


def _fold_length_marks(text: str) -> str:
    # Decompose so precomposed length letters (e.g. ῠ U+1FE0) expose their mark,
    # drop macron/breve only, recompose -- accents/breathings are other
    # codepoints and survive.
    decomposed = unicodedata.normalize("NFD", text).translate(_LENGTH_MARKS_TABLE)
    return unicodedata.normalize("NFC", decomposed)


def _normalize(text: str, fold: bool) -> str:
    """Stress-strip always; length-fold for grc-like langs (`fold`)."""
    text = _strip_stress_marks(text)
    return _fold_length_marks(text) if fold else text


# A form with one parenthesized optional letter group (grc movable nu "ἦ(ν)")
# is unreachable as a literal key: expand to both spellings. Multi-group or
# alternative shapes are annotation leakage and stay untouched.
_OPTIONAL_GROUP = re.compile(r"^([^()]*)\(([^()/]{1,3})\)([^()]*)$")


def _expand_optional_group(form: str) -> list[str]:
    match = _OPTIONAL_GROUP.match(form)
    if match is None:
        return [form]
    head, opt, tail = match.groups()
    return [head + tail, head + opt + tail]


def _extract_pairs_raw(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs, preferring form_of/alt_of over forms.
    May repeat a pair across senses of the same entry -- extract_pairs dedups.
    An entry left with no pairs yields its own identity pair: uninflected
    headwords (grc μέν) would otherwise never enter the dictionary."""
    word = entry.get("word")
    if not word:
        return

    lang_code = entry.get("lang_code")
    fold = lang_code in _LENGTH_MARK_LANGS
    drop_unrecognized = lang_code in _DROP_UNRECOGNIZED_FORM_LANGS
    norm_word = _normalize(word, fold)

    found_relation = False
    for relation_source in (entry, *entry.get("senses", ())):
        refs = relation_source.get("form_of") or relation_source.get("alt_of")
        for ref in refs or ():
            ref_word = ref.get("word")
            if ref_word:
                yield (_normalize(ref_word, fold), norm_word)
                found_relation = True

    if found_relation:
        return

    yielded_form = False
    dropped_junk = False
    for form in entry.get("forms", ()):
        word_form = form.get("form")
        tags = form.get("tags", ())
        if not word_form or word_form == _PLACEHOLDER_FORM:
            continue
        if _UNCONDITIONAL_DROP_TAGS.intersection(tags) or (
            drop_unrecognized and "error-unrecognized-form" in tags
        ):
            dropped_junk = True
            continue
        if word_form != word and _CROSS_REFERENCE_TAGS.intersection(tags):
            continue
        for variant in _expand_optional_group(word_form):
            yield (norm_word, _normalize(variant, fold))
        yielded_form = True
    # Identity fallback for uninflected headwords (grc μέν) -- but never after
    # a junk-tag drop, which must not resurrect as an identity key. The
    # fallback also votes in resolution ties; the per-language gates cover it.
    if not yielded_form and not dropped_junk:
        yield (norm_word, norm_word)


def extract_pairs(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs, preferring form_of/alt_of over forms.

    Dedups pairs repeated across senses of the same entry -- dictionary_builder's
    R2 resolution treats line count as evidence, so a repeat must not count
    as a second attestation."""
    yield from dict.fromkeys(_extract_pairs_raw(entry))


def main(input_path: Path, output_path: Path) -> None:
    log.info(f"Extracting pairs from {input_path}")
    with open(input_path, encoding="utf-8") as infh:
        pairs = (pair for line in infh for pair in extract_pairs(json.loads(line)))
        pair_count = write_pairs(pairs, output_path)
    log.info(f"Wrote {pair_count} pairs to {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="kaikki.org JSONL dump")
    parser.add_argument("output", type=Path, help="output TSV path (lemma TAB word)")
    args = parser.parse_args()
    main(args.input, args.output)
