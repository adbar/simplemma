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
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Tags marking rows that are never real inflected forms.
_UNCONDITIONAL_DROP_TAGS = frozenset(
    {
        "table-tags",
        "inflection-template",
        "class",
        "romanization",
        "transliteration",
    }
)

# Cross-reference rows (e.g. a pronoun's page listing other pronouns);
# dropped only when the form differs from the entry's own word, so a
# genuine self-mapping keeps its vote in dictionary_builder's resolution.
_CROSS_REFERENCE_TAGS = frozenset({"pronoun", "possessive", "auxiliary"})

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


def _extract_pairs_raw(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs, preferring form_of/alt_of over forms.
    May repeat a pair across senses of the same entry -- extract_pairs dedups."""
    word = entry.get("word")
    if not word:
        return

    fold = entry.get("lang_code") in _LENGTH_MARK_LANGS
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

    for form in entry.get("forms", ()):
        word_form = form.get("form")
        tags = form.get("tags", ())
        if (
            not word_form
            or word_form == _PLACEHOLDER_FORM
            or _UNCONDITIONAL_DROP_TAGS.intersection(tags)
            or (word_form != word and _CROSS_REFERENCE_TAGS.intersection(tags))
        ):
            continue
        yield (norm_word, _normalize(word_form, fold))


def extract_pairs(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs, preferring form_of/alt_of over forms.

    Dedups pairs repeated across senses of the same entry -- dictionary_builder's
    R2 resolution treats line count as evidence, so a repeat must not count
    as a second attestation."""
    yield from dict.fromkeys(_extract_pairs_raw(entry))


def main(input_path: Path, output_path: Path) -> None:
    log.info(f"Extracting pairs from {input_path}")
    pair_count = 0
    with (
        open(input_path, encoding="utf-8") as infh,
        open(output_path, "w", encoding="utf-8") as outfh,
    ):
        for line in infh:
            for lemma, word_form in extract_pairs(json.loads(line)):
                outfh.write(f"{lemma}\t{word_form}\n")
                pair_count += 1
    log.info(f"Wrote {pair_count} pairs to {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="kaikki.org JSONL dump")
    parser.add_argument("output", type=Path, help="output TSV path (lemma TAB word)")
    args = parser.parse_args()
    main(args.input, args.output)
