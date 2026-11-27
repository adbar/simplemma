"""Convert a kaikki.org JSONL Wiktionary dump into a lemma<TAB>form word list."""

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

_UNCONDITIONAL_DROP_TAGS = frozenset(
    {
        "table-tags",
        "inflection-template",
        "class",
        "Baybayin",
    }
)

# Verb and adjective forms in 다 also yield their stem (했다 -> 했).
_STEM_KEY_ENDINGS = {"ko": "다"}
_STEM_KEY_POS = frozenset({"verb", "adj"})

# Inflected-form entries, skipped when they lack a form-of link (몰라요, 했다).
_FORM_TEMPLATES = frozenset({"ko-verb-form", "ko-adj-form"})

# Cross-reference and reading rows, dropped only when the form differs from the word.
_CROSS_REFERENCE_TAGS = frozenset(
    {"pronoun", "possessive", "auxiliary", "romanization", "transliteration"}
)


# Junk only on tl verb pages, it tags real forms elsewhere (cy mutation).
_DROP_UNRECOGNIZED_FORM_LANGS = frozenset({"tl"})

_PLACEHOLDER_FORM = "-"  # marks a form that doesn't exist for this word

# Combining grave/acute only, precomposed Latin/Greek accents are kept.
_STRESS_MARKS_TABLE = str.maketrans("", "", "̀́")


# Not global: macron is orthographic in e.g. Latvian.
_LENGTH_MARK_LANGS = {"grc"}
_LENGTH_MARKS_TABLE = str.maketrans("", "", "̄̆")  # combining macron, breve


def _fold_length_marks(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text).translate(_LENGTH_MARKS_TABLE)
    return unicodedata.normalize("NFC", decomposed)


def _normalize(text: str, fold: bool) -> str:
    """Strip stress marks, and length marks too if `fold`."""
    # NFC first so precomposed accents are not stripped.
    text = unicodedata.normalize("NFC", text).translate(_STRESS_MARKS_TABLE)
    return _fold_length_marks(text) if fold else text


# One optional letter group like grc "ἦ(ν)" expands to both spellings.
_OPTIONAL_GROUP = re.compile(r"^([^()]*)\(([^()/]{1,3})\)([^()]*)$")


def _expand_optional_group(form: str) -> list[str]:
    match = _OPTIONAL_GROUP.match(form)
    if match is None:
        return [form]
    head, opt, tail = match.groups()
    return [head + tail, head + opt + tail]


def _extract_pairs_raw(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield possibly repeated (lemma, word_form) pairs, see extract_pairs."""
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

    # Mixed entries (a form-of sense next to real senses) keep their forms.
    if found_relation and all(
        s.get("form_of") or s.get("alt_of") for s in entry.get("senses", ())
    ):
        return
    if any(t.get("name") in _FORM_TEMPLATES for t in entry.get("head_templates", ())):
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
    # Identity for uninflected headwords, but not after a junk drop.
    if not yielded_form and not dropped_junk:
        yield (norm_word, norm_word)


def extract_pairs(entry: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield unique (lemma, word_form) pairs, form_of/alt_of links before forms.

    Duplicates must not count as extra attestations downstream."""
    pairs = dict.fromkeys(_extract_pairs_raw(entry))
    ending = _STEM_KEY_ENDINGS.get(entry.get("lang_code", ""))
    if ending and entry.get("pos") in _STEM_KEY_POS:
        word = _normalize(entry.get("word") or "", False)
        bases = list(pairs)
        # The headword counts as a form, unless form-of/alt-of or nothing yielded.
        if bases and all(lemma == word for lemma, _ in bases):
            bases.append((word, word))
        for lemma, form in bases:
            if len(form) > len(ending) and form.endswith(ending):
                pairs.setdefault((lemma, form[: -len(ending)]))
    yield from pairs


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
