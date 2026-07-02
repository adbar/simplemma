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

# Never real inflected forms: structural placeholders/template names
# ("table-tags", "inflection-template"), a verb-class label ("class"), or
# a transliteration into another script ("romanization"/"transliteration").
_UNCONDITIONAL_DROP_TAGS = frozenset(
    {
        "table-tags",
        "inflection-template",
        "class",
        "romanization",
        "transliteration",
    }
)

# Marks a whole-paradigm cross-reference row (e.g. a pronoun's page listing
# other pronouns, or a verb's auxiliary) rather than an inflection of the
# entry. Only drop when the form differs from the entry's own word: a
# genuine self-mapping must keep its vote in dictionary_pickler's
# evidence-count resolution, or an unrelated candidate can win instead.
_CROSS_REFERENCE_TAGS = frozenset({"pronoun", "possessive", "auxiliary"})

# Placeholder for a form that doesn't exist for this word in a declension
# table (distinct from "error-unrecognized-form", which flags real forms).
_PLACEHOLDER_FORM = "-"

# Cyrillic word-stress combining accents, absent from running text. Deleted
# as literal codepoints rather than via an NFD/NFC round-trip: Latin
# precomposed accents (café) would decompose into the same codepoints and
# get stripped too.
_STRESS_MARKS_TABLE = str.maketrans("", "", "̀́")


def _strip_stress_marks(text: str) -> str:
    return text.translate(_STRESS_MARKS_TABLE)


def extract_pairs(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs for a single kaikki.org entry.

    Prefers explicit `form_of`/`alt_of` relations; falls back to the
    entry's own `forms` table only if none were found, since `forms` also
    lists non-inflectional rows for entries that are themselves lemmas.
    """
    word = entry.get("word")
    if not word:
        return
    stripped_word = _strip_stress_marks(word)

    found_relation = False
    for relation_source in (entry, *entry.get("senses", ())):
        refs = relation_source.get("form_of") or relation_source.get("alt_of")
        if refs and refs[0].get("word"):
            yield (_strip_stress_marks(refs[0]["word"]), stripped_word)
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
