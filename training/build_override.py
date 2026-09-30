"""Mine a form to lemma override lexicon for one language from UD train splits.

A form keeps its majority lemma when the pooled evidence clears its POS-class
bar and no often-attesting treebank disagrees. Shipping still requires a
dictionary rebuild.

Usage: uv run python -m training.build_override <lang> [--in-place]
"""

import argparse
import logging
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from training.clean_wordlist import pair_violation, write_pairs
from training.dictionary_builder import OVERRIDES_DIR, _canon, _layer_entries
from training.ud_conllu import discover_treebanks, iter_word_tokens

log = logging.getLogger(__name__)

# Closed-class words are convention-stable at lower evidence.
CLOSED_CLASS_POS = frozenset({"PRON", "DET", "ADP", "CCONJ", "SCONJ", "AUX", "PART"})
CLOSED_MIN_COUNT, CLOSED_MIN_AGREEMENT = 3, 0.90
OPEN_MIN_COUNT, OPEN_MIN_AGREEMENT = 5, 0.95
TREEBANK_MIN_COUNT = 3

OUTPUT_DIR = Path(__file__).parent / "output"

Counts = dict[str, Counter[str]]


def collect_candidates(
    train_paths: list[Path], lang: str
) -> tuple[list[Counts], Counts]:
    """Form to lemma counts per treebank, and form to POS counts."""
    pos: defaultdict[str, Counter[str]] = defaultdict(Counter)
    per_treebank: list[Counts] = []
    for path in train_paths:
        counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for form, token in iter_word_tokens(path, lang):
            if not any(ch.isalpha() for ch in form):
                continue
            counts[form][token["lemma"]] += 1
            pos[form][token["upos"]] += 1
        per_treebank.append(dict(counts))
    return per_treebank, dict(pos)


def resolve_overrides(per_treebank: list[Counts], pos: Counts) -> dict[str, str]:
    """Pooled majority lemma per form, kept if it clears the bar unvetoed.

    Ties are deterministic and a POS tie takes the stricter open-class bar."""
    pooled: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for treebank_counts in per_treebank:
        for form, lemma_counts in treebank_counts.items():
            pooled[form].update(lemma_counts)
    overrides = {}
    for form, counts in pooled.items():
        total = sum(counts.values())
        top, lemma = max((n, lem) for lem, n in counts.items())
        top_pos = max(pos[form].values())
        closed = all(
            upos in CLOSED_CLASS_POS for upos, n in pos[form].items() if n == top_pos
        )
        min_count, min_agreement = (
            (CLOSED_MIN_COUNT, CLOSED_MIN_AGREEMENT)
            if closed
            else (OPEN_MIN_COUNT, OPEN_MIN_AGREEMENT)
        )
        if total < min_count or top / total < min_agreement:
            continue
        if any(
            sum(tb[form].values()) >= TREEBANK_MIN_COUNT
            and tb[form][lemma] < max(tb[form].values())
            for tb in per_treebank
            if form in tb
        ):
            continue
        overrides[form] = lemma
    return overrides


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
    args = parser.parse_args()
    lang = args.lang

    train_paths = discover_treebanks(lang, split="train")
    if not train_paths:
        sys.exit(f"no -ud-train split found for {lang!r}")
    candidates = resolve_overrides(*collect_candidates(train_paths, lang))
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
