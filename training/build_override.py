"""Mine a form to lemma override lexicon for one language from UD train splits.

A form gets its majority lemma when the pooled evidence clears its POS-class
bar and the lemma beats the current output, overall and in every
often-attesting treebank. Shipping still requires a dictionary rebuild.

Usage: uv run python -m training.build_override <lang> [--exclude TREEBANK]... [--in-place]
"""

import argparse
import logging
import shutil
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

from simplemma import lemmatize
from training.clean_wordlist import pair_violation, write_pairs
from training.dictionary_builder import OVERRIDES_DIR, _canon, _layer_entries
from training.ud_conllu import dataset_name, discover_treebanks, iter_word_tokens

log = logging.getLogger(__name__)

# Closed-class words are convention-stable at lower evidence.
CLOSED_CLASS_POS = frozenset({"PRON", "DET", "CCONJ", "SCONJ", "AUX", "PART"})
CLOSED_MIN_COUNT, OPEN_MIN_COUNT = 3, 5
MIN_AGREEMENT = 0.6
MIN_GAIN = 2
TREEBANK_MIN_COUNT = 3
# Left to runtime casing and treebank conventions.
PARTICIPLE = "VerbForm=Part"
EXCLUDED_TAGS = frozenset({"PROPN", "ADP", PARTICIPLE})

OUTPUT_DIR = Path(__file__).parent / "output"

Counts = dict[str, Counter[str]]
Tags = dict[str, set[str]]


def top_tags(pos_counts: Counter[str]) -> set[str]:
    top = max(pos_counts.values())
    return {tag for tag, n in pos_counts.items() if n == top}


def collect_candidates(train_paths: list[Path], lang: str) -> tuple[list[Counts], Tags]:
    """Form to lemma counts per treebank, and form to top POS tags, in key space.

    Participles count under PARTICIPLE instead of their UPOS."""
    pos: defaultdict[str, Counter[str]] = defaultdict(Counter)
    per_treebank: list[Counts] = []
    for path in train_paths:
        counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for form, token in iter_word_tokens(path, lang):
            if not any(ch.isalpha() for ch in form):
                continue
            form = _canon(form, lang)
            counts[form][_canon(token["lemma"], lang)] += 1
            feats = token["feats"] or {}
            tag = PARTICIPLE if feats.get("VerbForm") == "Part" else token["upos"]
            pos[form][tag] += 1
        per_treebank.append(dict(counts))
    return per_treebank, {form: top_tags(counts) for form, counts in pos.items()}


def pool(per_treebank: list[Counts]) -> Counts:
    pooled: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for treebank_counts in per_treebank:
        for form, lemma_counts in treebank_counts.items():
            pooled[form].update(lemma_counts)
    return dict(pooled)


def majority(counts: Counter[str]) -> tuple[str, float]:
    """Majority lemma up to case, in its most frequent casing, and its share."""
    folded: Counter[str] = Counter()
    for lem, n in counts.items():
        folded[lem.lower()] += n
    top, key = max((n, k) for k, n in folded.items())
    _, lemma = max((n, lem) for lem, n in counts.items() if lem.lower() == key)
    return lemma, top / sum(counts.values())


def votes(counts: Counter[str], lemma: str) -> int:
    """Count of `lemma` up to case."""
    return sum(n for lem, n in counts.items() if lem.lower() == lemma.lower())


def skipped(form: str, lemma: str, tags: set[str]) -> bool:
    """Excluded tag, sentence-initial artifact, multiword, letterless or unshippable."""
    return bool(
        tags & EXCLUDED_TAGS
        or (form == form.lower() and lemma != lemma.lower())
        or ("_" in lemma and "_" not in form)
        or not any(ch.isalpha() for ch in lemma)
        or " " in form + lemma
        or pair_violation(lemma, form)
    )


def min_count(tags: set[str]) -> int:
    return CLOSED_MIN_COUNT if tags <= CLOSED_CLASS_POS else OPEN_MIN_COUNT


def clear_majority(form: str, counts: Counter[str], tags: set[str]) -> str | None:
    """Majority lemma if it clears the bars and is not skipped, else None."""
    lemma, share = majority(counts)
    if (
        sum(counts.values()) < min_count(tags)
        or share < MIN_AGREEMENT
        or skipped(form, lemma, tags)
    ):
        return None
    return lemma


def contradicts_lowercase(
    form: str, lemma: str, tags: set[str], pooled: Counts, form_tags: Tags
) -> bool:
    """Lemma is the lowercased form, but that form has another majority lemma."""
    lower = form.lower()
    return (
        lemma == lower
        and lower in pooled
        and bool(form_tags[lower] & tags)
        and majority(pooled[lower])[0].lower() != lower
    )


def resolve_overrides(
    per_treebank: list[Counts], form_tags: Tags, current: Callable[[str], str]
) -> dict[str, str]:
    """Pooled majority lemma per form, kept if it clears the bar and beats `current`.

    A POS tie takes the stricter open-class bar and is skipped on any excluded
    tag. Lemma and output count up to case, and case-only changes are left to
    the runtime."""
    overrides = {}
    pooled = pool(per_treebank)
    for form, counts in pooled.items():
        tags = form_tags[form]
        lemma = clear_majority(form, counts, tags)
        if lemma is None or contradicts_lowercase(form, lemma, tags, pooled, form_tags):
            continue
        output = current(form)

        def gain(c: Counter[str]) -> int:
            return votes(c, lemma) - votes(c, output)

        if gain(counts) < MIN_GAIN or any(
            sum(c.values()) >= TREEBANK_MIN_COUNT and gain(c) < 0
            for tb in per_treebank
            if (c := tb.get(form))
        ):
            continue
        overrides[form] = lemma
    return overrides


def report_contradictions(
    pooled: Counts, form_tags: Tags, existing: dict[str, str], lang: str
) -> None:
    """Warn on existing entries whose form has another clear UD majority."""
    for form in sorted(existing.keys() & pooled.keys()):
        counts = pooled[form]
        lemma = clear_majority(form, counts, form_tags[form])
        if lemma is not None and lemma.lower() != existing[form].lower():
            log.warning(
                "%s: UD prefers %r over existing %r for %r (%d%% of %d)",
                lang,
                lemma,
                existing[form],
                form,
                round(100 * majority(counts)[1]),
                sum(counts.values()),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Update training/overrides/<lang>.tsv "
        "(default: write the candidate to training/output/ only).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="TREEBANK",
        help="Treebank to leave out, e.g. fr_alts. Repeatable.",
    )
    args = parser.parse_args()
    lang = args.lang

    all_paths = discover_treebanks(lang, split="train")
    if not all_paths:
        sys.exit(f"no -ud-train split found for {lang!r}")
    unknown = set(args.exclude) - {dataset_name(path) for path in all_paths}
    if unknown:
        sys.exit(f"unknown treebanks for {lang!r}: {', '.join(sorted(unknown))}")
    train_paths = [path for path in all_paths if dataset_name(path) not in args.exclude]
    per_treebank, form_tags = collect_candidates(train_paths, lang)
    path = OVERRIDES_DIR / f"{lang}.tsv"
    existing = _layer_entries(path, lang)
    report_contradictions(pool(per_treebank), form_tags, existing, lang)
    candidates = resolve_overrides(
        per_treebank, form_tags, lambda form: lemmatize(form, lang)
    )
    merged = candidates | existing
    n_added = len(merged) - len(existing)
    log.info(f"{lang}: {n_added} new entries over {len(existing)} existing")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{lang}.tsv"
    write_pairs(((lemma, form) for form, lemma in sorted(merged.items())), out_path)
    log.info(f"candidate written to {out_path}")
    if args.in_place:
        shutil.copy(out_path, path)
        log.info(f"updated {path} -- rebuild the dictionary to ship")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
