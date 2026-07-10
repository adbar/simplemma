"""
Convert a kaikki.org JSONL Wiktionary dump into a lemma-form TSV word list
suitable as input for `dictionary_pickler.py` (see training/README.rst for
the full data-preparation pipeline this script is one step of).

Input format: one JSON object per line, as downloaded from kaikki.org.
Output format: lemma, tab, word form, newline.
"""

import argparse
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
# genuine self-mapping keeps its vote in dictionary_pickler's resolution.
_CROSS_REFERENCE_TAGS = frozenset({"pronoun", "possessive", "auxiliary"})

_PLACEHOLDER_FORM = "-"  # marks a form that doesn't exist for this word

# literal codepoints, not NFD/NFC: that would also strip Latin precomposed accents
_STRESS_MARKS_TABLE = str.maketrans("", "", "̀́")


def _strip_stress_marks(text: str) -> str:
    return text.translate(_STRESS_MARKS_TABLE)


def _extract_pairs_raw(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs, preferring form_of/alt_of over forms.

    May repeat a pair across senses of the same entry -- extract_pairs dedups.
    """
    word = entry.get("word")
    if not word:
        return
    stripped_word = _strip_stress_marks(word)

    found_relation = False
    for relation_source in (entry, *entry.get("senses", ())):
        refs = relation_source.get("form_of") or relation_source.get("alt_of")
        for ref in refs or ():
            ref_word = ref.get("word")
            if ref_word:
                yield (_strip_stress_marks(ref_word), stripped_word)
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
        yield (stripped_word, _strip_stress_marks(word_form))


def extract_pairs(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs, preferring form_of/alt_of over forms.

    Deduplicates pairs repeated across senses of the SAME entry, so a pair's
    line count in the output TSV reflects independent attestations --
    dictionary_pickler's R2 resolution treats line count as evidence, and a
    single entry describing its own relation twice is not two attestations.
    """
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="kaikki.org JSONL dump")
    parser.add_argument("output", type=Path, help="output TSV path (lemma TAB word)")
    args = parser.parse_args()
    main(args.input, args.output)
