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

# Kaikki "forms" rows carrying either of these tags are structural
# placeholders (a table's own header/template name), not real inflected
# forms — e.g. form="no-table-tags" (tag "table-tags") or a literal
# template name like form="ro-noun-n-uri" (tag "inflection-template").
_META_TAGS = frozenset({"table-tags", "inflection-template"})

# Literal placeholder used in declension tables for a form that doesn't
# exist for this word (e.g. an adjective with no definite form). Distinct
# from the "error-unrecognized-form" tag, which mostly flags real forms
# the parser merely wasn't fully confident about and must not be filtered.
_PLACEHOLDER_FORM = "-"


def extract_pairs(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (lemma, word_form) pairs for a single kaikki.org entry.

    Prefers explicit inflection relations (`form_of`/`alt_of`, either on the
    entry itself or nested in one of its `senses`, meaning the entry is an
    inflected form); falls back to the entry's own `forms` table only if
    none were found, since `forms` also lists non-inflectional rows for
    entries that are themselves lemmas.
    """
    word = entry.get("word")
    if not word:
        return

    found_relation = False
    for relation_source in (entry, *entry.get("senses", ())):
        refs = relation_source.get("form_of") or relation_source.get("alt_of")
        if refs and refs[0].get("word"):
            yield (refs[0]["word"], word)
            found_relation = True

    if found_relation:
        return

    for form in entry.get("forms", ()):
        word_form = form.get("form")
        if (
            not word_form
            or word_form == _PLACEHOLDER_FORM
            or _META_TAGS.intersection(form.get("tags", ()))
        ):
            continue
        yield (word, word_form)


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
