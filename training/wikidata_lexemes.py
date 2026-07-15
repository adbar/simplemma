"""
Extract (lemma, form) pairs for one language from a Wikidata lexeme dump
(`latest-lexemes.json.gz`, dumps.wikimedia.org/wikidatawiki/entities/), for
use as an OOV-fill source layered onto (never overriding) a shipped
dictionary. Wikidata precision is consistently higher than the shipped
dict itself, but coverage is lexicon-dependent -- fill only, no
full-rebuild, never override a collision.

Dump format: a JSON array serialized one object per line (`[`, then one
`{...},` per line, then `]`) -- not true JSONL, but each line parses on its
own once the leading/trailing punctuation is stripped.

Per-lexeme schema (verified against a live dump):
    {"language": "<QID>", "lemmas": {"<lang_code>": {"value": "<lemma>"}},
     "forms": [{"representations": {"<lang_code>": {"value": "<form>"}}}]}
"""

import argparse
import gzip
import json
import logging
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from simplemma.strategies import DefaultStrategy
from simplemma.strategies.dictionaries.dictionary_factory import (
    _load_dictionary_from_disk,
)
from training.clean_wordlist import check_field
from training.eval_harness import FixedDictionaryFactory

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Languages with a verified Wikidata QID (i.e. everything extractable).
LANGUAGE_QIDS = {
    "de": "Q188",
    "ru": "Q7737",
    "da": "Q9035",
    "et": "Q9072",
    "en": "Q1860",
    "it": "Q652",
    "es": "Q1321",
    "la": "Q397",
    "sv": "Q9027",
    "el": "Q36510",
    "nb": "Q25167",
    "cs": "Q9056",
    "nl": "Q7411",
    # mid-tier by lexeme count; below ~1k lexemes yields ~0 fill pairs.
    "fr": "Q150",
    "sk": "Q9058",
    "uk": "Q8798",
    "pt": "Q5146",
    "pl": "Q809",
    "fi": "Q1412",
    "tr": "Q256",
}

# Subset that ships Wikidata fill in v2.0 (gated by assess_wikidata_fill.py):
# fr/it/tr regress cross-treebank, nb has no UD treebank.
V2_FILL_LANGS = frozenset(
    {
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "fi",
        "la",
        "nl",
        "pl",
        "pt",
        "ru",
        "sk",
        "sv",
        "uk",
    }
)


def stream_lexemes(
    path: Path, prefilter: tuple[str, ...] | None = None
) -> Iterator[dict[str, Any]]:
    """Stream lexeme objects out of the gzip-compressed dump without loading it whole.

    `prefilter`, if given, is a tuple of literal substrings (e.g.
    '"language":"Q188"'); a line is skipped without ever calling json.loads
    unless it contains at least one of them. Most lexemes carry a large
    `claims` blob a full parse builds and immediately discards for every
    line that doesn't match -- worth it when filtering to a handful of
    languages out of the whole dump (see extract_language's typical use).
    """
    with gzip.open(path, "rt", encoding="utf-8") as filehandle:
        for line in filehandle:
            if prefilter is not None and not any(
                needle in line for needle in prefilter
            ):
                continue
            line = line.strip()
            if line in ("[", "]", ""):
                continue
            yield json.loads(line.rstrip(","))


def extract_pairs(lexeme: dict[str, Any], lang_code: str) -> Iterator[tuple[str, str]]:
    """Yield (lemma, form) pairs for a lexeme's `lang_code` representations."""
    lemma = lexeme.get("lemmas", {}).get(lang_code, {}).get("value")
    if not lemma:
        return
    for form in lexeme.get("forms", ()):
        value = form.get("representations", {}).get(lang_code, {}).get("value")
        if value:
            yield (lemma, value)


def extract_language(
    dump_path: Path, language_qid: str, lang_code: str
) -> Iterator[tuple[str, str]]:
    """Extract every (lemma, form) pair for one language from the full dump."""
    needle = f'"language":"{language_qid}"'
    for lexeme in stream_lexemes(dump_path, prefilter=(needle,)):
        if lexeme.get("language") == language_qid:
            yield from extract_pairs(lexeme, lang_code)


def drop_ambiguous(
    pairs: Iterable[tuple[str, str]],
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Drop pairs where `form` is attested with more than one distinct lemma.

    Wikidata is high-precision but not conflict-free; unlike
    dictionary_pickler's R2, there's no evidence-count signal here to
    arbitrate a genuine ambiguity, so the safe choice is to drop it rather
    than guess (matches the research's "599,653 unambiguous pairs" method).
    """
    all_pairs = list(pairs)
    lemmas_by_form: defaultdict[str, set[str]] = defaultdict(set)
    for lemma, form in all_pairs:
        lemmas_by_form[form].add(lemma)
    ambiguous_forms = {
        form for form, lemmas in lemmas_by_form.items() if len(lemmas) > 1
    }
    kept = [pair for pair in all_pairs if pair[1] not in ambiguous_forms]
    stats = {
        "total_pairs": len(all_pairs),
        "ambiguous_forms": len(ambiguous_forms),
        "kept_pairs": len(kept),
    }
    return kept, stats


def drop_junk_pairs(
    pairs: Iterable[tuple[str, str]],
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Drop pairs with a mojibake/control-char lemma or form, so the written
    fill file is strict-readable by the pickler's read_pairs (which fails the
    build on such a field). Shares check_field, so this producer and that
    consumer agree by construction on what counts as junk."""
    all_pairs = list(pairs)
    kept = [
        (lemma, form)
        for lemma, form in all_pairs
        if not check_field(lemma) and not check_field(form)
    ]
    return kept, {"total": len(all_pairs), "kept": len(kept)}


def _prune_with_anchor(
    fill_pairs: list[tuple[str, str]], anchor: dict[str, str], lang: str
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Drop fill pairs the real lemmatization chain already reproduces from
    `anchor` alone (dict lookup + hyphen + rules + prefix + affix, no fill)."""
    strategy = DefaultStrategy(dictionary_factory=FixedDictionaryFactory(anchor))
    kept = []
    pruned = 0
    for lemma, form in fill_pairs:
        if strategy.get_lemma(form, lang) == lemma:
            pruned += 1
        else:
            kept.append((lemma, form))
    return kept, {"total": len(fill_pairs), "pruned": pruned, "kept": len(kept)}


def stem_anchored_prune(
    fill_pairs: list[tuple[str, str]], shipped: dict[str, str], lang: str
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Anchor on shipped + every fill lemma's own self-map, then keep only
    forms the affix chain still can't regenerate from those anchors alone.

    A RAM-only lever (front-coding makes full-fill smallest on disk, so we ship
    that): prunes ~half the entries, accuracy-neutral, most so for agglutinative
    languages where affix decomposition regenerates inflected forms from the
    base form.

    CRUCIAL: the fill-lemma self-maps that make the pruning safe are NOT
    guaranteed to be in `shipped`, so they must ship with the kept output --
    otherwise a pruned form regenerates to a base lemma absent from the
    final dict and lemmatizes to None.
    """
    fill_lemmas = {lemma for lemma, _ in fill_pairs}
    anchor = dict(shipped)
    for lemma in fill_lemmas:
        anchor.setdefault(lemma, lemma)
    kept, stats = _prune_with_anchor(fill_pairs, anchor, lang)
    # Re-add anchoring self-maps not in shipped (identity forms are always
    # derivable, so they never survive _prune). The pruning-safety invariant
    # requires L->L present, so a self-map must win over any surviving pair
    # whose FORM is L -- drop that conflicting pair explicitly rather than
    # relying on append order / last-writer (which would clobber it silently).
    self_map_lemmas = {lemma for lemma in fill_lemmas if lemma not in shipped}
    deconflicted = [(lem, form) for lem, form in kept if form not in self_map_lemmas]
    self_maps = [(lemma, lemma) for lemma in self_map_lemmas]
    stats["dropped_form_lemma_conflict"] = len(kept) - len(deconflicted)
    kept = deconflicted + self_maps
    stats["self_maps_added"] = len(self_maps)
    stats["kept"] = len(kept)
    return kept, stats


def shipped_dict_as_str_mapping(lang: str) -> dict[str, str]:
    """The real shipped dictionary for `lang`, decoded to a str->str mapping."""
    raw = _load_dictionary_from_disk(lang)
    return {k.decode(): v.decode() for k, v in raw.items()}


def write_tsv(pairs: Iterable[tuple[str, str]], output_path: Path) -> int:
    count = 0
    with open(output_path, "w", encoding="utf-8") as filehandle:
        for lemma, form in pairs:
            filehandle.write(f"{lemma}\t{form}\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang", choices=sorted(LANGUAGE_QIDS))
    parser.add_argument("dump", type=Path, help="Path to latest-lexemes.json.gz")
    parser.add_argument("output", type=Path, help="Output TSV path (lemma TAB form)")
    parser.add_argument(
        "--prune",
        choices=("none", "stem-anchored"),
        default="none",
        help="stem-anchored: drop fill pairs the shipped-dict+rules/affix chain "
        "already regenerates (RAM lever; we ship full-fill by default).",
    )
    args = parser.parse_args()

    log.info(f"Extracting {args.lang} pairs from {args.dump}...")
    raw_pairs = list(extract_language(args.dump, LANGUAGE_QIDS[args.lang], args.lang))
    log.info(f"Extracted {len(raw_pairs)} raw pairs")
    if not raw_pairs:
        # A dump-format change (e.g. whitespace in the JSON) would silently
        # defeat stream_lexemes' substring prefilter -- fail loud, don't ship
        # an empty fill that a long dump scan produced with no error.
        print(
            f"ERROR: extracted 0 pairs for {args.lang!r} -- wrong QID or "
            f"unexpected dump format ({args.dump})",
            file=sys.stderr,
        )
        sys.exit(1)

    kept_pairs, ambiguity_stats = drop_ambiguous(raw_pairs)
    log.info(f"Ambiguity filter: {ambiguity_stats}")

    if args.prune == "stem-anchored":
        shipped = shipped_dict_as_str_mapping(args.lang)
        kept_pairs, prune_stats = stem_anchored_prune(kept_pairs, shipped, args.lang)
        log.info(f"stem-anchored prune: {prune_stats}")

    kept_pairs, junk_stats = drop_junk_pairs(kept_pairs)
    log.info(f"Junk filter: {junk_stats}")

    count = write_tsv(kept_pairs, args.output)
    log.info(f"Wrote {count} pairs to {args.output}")


if __name__ == "__main__":
    main()
