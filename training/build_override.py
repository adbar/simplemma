"""Mine a form to lemma override lexicon for one language from UD train splits.

A form gets its majority lemma when the pooled evidence clears its POS-class
bar and the lemma beats the current output, overall and in every
often-attesting treebank. Shipping still requires a dictionary rebuild.

Usage: uv run python -m training.build_override <lang> [--exclude TREEBANK ...] [--in-place]
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
CLOSED_CLASS_POS = frozenset({"PRON", "DET", "ADP", "CCONJ", "SCONJ", "AUX", "PART"})
CLOSED_MIN_COUNT, OPEN_MIN_COUNT = 3, 5
MIN_AGREEMENT = 0.6
MIN_GAIN = 2
TREEBANK_MIN_COUNT = 3
# Left to runtime casing and treebank conventions.
PARTICIPLE = "Part"
EXCLUDED_TAGS = frozenset({"PROPN", "ADP", PARTICIPLE})

OUTPUT_DIR = Path(__file__).parent / "output"

Counts = dict[str, Counter[str]]


def collect_candidates(
    train_paths: list[Path], lang: str
) -> tuple[list[Counts], Counts]:
    """Form to lemma counts per treebank, and form to POS counts.

    Participles count under PARTICIPLE instead of their UPOS."""
    pos: defaultdict[str, Counter[str]] = defaultdict(Counter)
    per_treebank: list[Counts] = []
    for path in train_paths:
        counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for form, token in iter_word_tokens(path, lang):
            if not any(ch.isalpha() for ch in form):
                continue
            counts[form][token["lemma"]] += 1
            feats = token["feats"] or {}
            tag = PARTICIPLE if feats.get("VerbForm") == "Part" else token["upos"]
            pos[form][tag] += 1
        per_treebank.append(dict(counts))
    return per_treebank, dict(pos)


def pool(per_treebank: list[Counts]) -> Counts:
    pooled: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for treebank_counts in per_treebank:
        for form, lemma_counts in treebank_counts.items():
            pooled[form].update(lemma_counts)
    return dict(pooled)


def majority(counts: Counter[str]) -> tuple[str, float]:
    """Majority lemma and its share, ties broken deterministically."""
    top, lemma = max((n, lem) for lem, n in counts.items())
    return lemma, top / sum(counts.values())


def resolve_overrides(
    per_treebank: list[Counts], pos: Counts, current: Callable[[str], str]
) -> dict[str, str]:
    """Pooled majority lemma per form, kept if it clears the bar and beats `current`.

    A POS tie takes the stricter open-class bar and is excluded on any excluded
    tag. Case-only changes are left to the runtime, and underscore-joined
    multiword lemmas are skipped."""
    overrides = {}
    for form, counts in pool(per_treebank).items():
        lemma, share = majority(counts)
        top_pos = max(pos[form].values())
        top_tags = {tag for tag, n in pos[form].items() if n == top_pos}
        min_count = CLOSED_MIN_COUNT if top_tags <= CLOSED_CLASS_POS else OPEN_MIN_COUNT
        if (
            sum(counts.values()) < min_count
            or share < MIN_AGREEMENT
            or top_tags & EXCLUDED_TAGS
            or ("_" in lemma and "_" not in form)
        ):
            continue
        output = current(form)
        if lemma.lower() == output.lower() or counts[lemma] - counts[output] < MIN_GAIN:
            continue
        if any(
            sum(tb[form].values()) >= TREEBANK_MIN_COUNT
            and tb[form][lemma] < tb[form][output]
            for tb in per_treebank
            if form in tb
        ):
            continue
        overrides[form] = lemma
    return overrides


def report_contradictions(
    per_treebank: list[Counts], lang: str, overrides_dir: Path | None = None
) -> None:
    """Warn on existing entries whose form has another clear UD majority."""
    path = (overrides_dir or OVERRIDES_DIR) / f"{lang}.tsv"
    existing = _layer_entries(path, lang) if path.exists() else {}
    for form, counts in sorted(pool(per_treebank).items()):
        line = existing.get(_canon(form, lang))
        total = sum(counts.values())
        if line is None or total < OPEN_MIN_COUNT:
            continue
        lemma, share = majority(counts)
        if share >= MIN_AGREEMENT and _canon(lemma, lang).lower() != line.lower():
            log.warning(
                "%s: UD prefers %r over existing %r for %r (%d%% of %d)",
                lang,
                lemma,
                line,
                form,
                round(100 * share),
                total,
            )


def merge_with_existing(
    candidates: dict[str, str], lang: str, overrides_dir: Path | None = None
) -> tuple[dict[str, str], int]:
    """Merge canonicalized candidates under existing entries, return (merged, n_added).

    Candidates that read_pairs would reject are skipped."""
    path = (overrides_dir or OVERRIDES_DIR) / f"{lang}.tsv"
    existing = _layer_entries(path, lang) if path.exists() else {}
    added = 0
    merged = dict(existing)
    for form, lemma in candidates.items():
        cform = _canon(form, lang)
        clemma = _canon(lemma, lang)
        if " " in cform or " " in clemma or pair_violation(clemma, cform):
            continue
        if cform in merged:
            if cform not in existing and merged[cform] != clemma:
                log.warning(
                    "%s: candidates collide on canonical key %r: kept %r, dropped %r",
                    lang,
                    cform,
                    merged[cform],
                    clemma,
                )
            continue
        merged[cform] = clemma
        added += 1
    return merged, added


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
        nargs="+",
        default=[],
        metavar="TREEBANK",
        help="Treebanks to leave out, e.g. fr_alts.",
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
    if not train_paths:
        sys.exit(f"all -ud-train splits excluded for {lang!r}")
    per_treebank, pos = collect_candidates(train_paths, lang)
    report_contradictions(per_treebank, lang)
    candidates = resolve_overrides(
        per_treebank, pos, lambda form: lemmatize(form, lang)
    )
    merged, n_added = merge_with_existing(candidates, lang)
    log.info(f"{lang}: {n_added} new entries over {len(merged) - n_added} existing")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{lang}.tsv"
    write_pairs(((lemma, form) for form, lemma in sorted(merged.items())), out_path)
    log.info(f"candidate written to {out_path}")
    if args.in_place:
        shutil.copy(out_path, OVERRIDES_DIR / f"{lang}.tsv")
        log.info(
            f"updated {OVERRIDES_DIR / f'{lang}.tsv'} -- rebuild the dictionary to ship"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
