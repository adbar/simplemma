"""Mine a reviewed override lexicon (form -> lemma) for one language from its
UD train splits, and gate it end-to-end before it can ship.

Methodology (validated 2026-08: 7 closed-class languages, then the la
open-class wave, README la 0.85 -> 0.90): pool every -ud-train split; keep a
form's majority lemma when the pooled evidence is strong enough for its POS
class AND every treebank that sees the form often enough agrees on the same
lemma. The per-treebank rule removes cross-treebank convention splits (la
"esse" ittb-vs-rest, fr "se" -> soi vs se) -- exactly the entries that would
not transfer. Only forms the shipped pipeline currently gets wrong are kept,
so the file stays a reviewable delta.

Usage: uv run python -m training.build_override <lang> [--in-place]

The merged candidate file (existing overrides + mined additions) is gated
with eval_gate on every test treebank; output goes to training/output/
unless --in-place updates training/overrides/<lang>.tsv. Shipping the effect
still requires a dictionary rebuild (python -m training.dictionary_builder,
--base shipped or merged, --in-place).
"""

import argparse
import logging
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from simplemma.utils import canonicalize_token
from training.clean_wordlist import write_pairs
from training.dictionary_builder import (
    OVERRIDES_DIR,
    _compose_dictionary,
    _layer_entries,
)
from training.eval_gate import (
    DEFAULT_EPSILON,
    discover_treebanks,
    gate,
    report_results,
)
from training.eval_harness import build_strategy
from training.ud_conllu import iter_word_tokens

log = logging.getLogger(__name__)

# Closed-class words are convention-stable at lower evidence; anything else
# needs more occurrences and stricter agreement.
CLOSED_CLASS_POS = frozenset({"PRON", "DET", "ADP", "CCONJ", "SCONJ", "AUX", "PART"})
CLOSED_MIN_COUNT, CLOSED_MIN_AGREEMENT = 3, 0.90
OPEN_MIN_COUNT, OPEN_MIN_AGREEMENT = 5, 0.95
# A treebank gets a veto once it has seen the form this often.
TREEBANK_MIN_COUNT = 3

OUTPUT_DIR = Path(__file__).parent / "output"

Counts = dict[str, Counter[str]]


def collect_candidates(
    train_paths: list[Path], lang: str
) -> tuple[list[Counts], Counts]:
    """(form->lemma counts per treebank, form->POS counts), letter-carrying
    forms only. Lemmas arrive canonicalized for `lang` via iter_word_tokens,
    so mined entries live in the shipped dict's key space."""
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
    """One form -> its majority lemma over the pooled treebanks, kept only
    when the pooled evidence clears the POS-class bar and no sufficiently-
    attesting treebank disagrees."""
    pooled: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for treebank_counts in per_treebank:
        for form, lemma_counts in treebank_counts.items():
            pooled[form].update(lemma_counts)
    overrides = {}
    for form, counts in pooled.items():
        total = sum(counts.values())
        lemma, top = counts.most_common(1)[0]
        closed = pos[form].most_common(1)[0][0] in CLOSED_CLASS_POS
        min_count, min_agreement = (
            (CLOSED_MIN_COUNT, CLOSED_MIN_AGREEMENT)
            if closed
            else (OPEN_MIN_COUNT, OPEN_MIN_AGREEMENT)
        )
        if total < min_count or top / total < min_agreement:
            continue
        if any(
            sum(tb[form].values()) >= TREEBANK_MIN_COUNT
            and tb[form].most_common(1)[0][0] != lemma
            for tb in per_treebank
            if form in tb
        ):
            continue
        overrides[form] = lemma
    return overrides


def merge_with_existing(
    candidates: dict[str, str], lang: str, overrides_dir: Path = OVERRIDES_DIR
) -> tuple[dict[str, str], int]:
    """Existing reviewed entries win their forms; candidates are folded into
    the runtime key space before comparison. Returns (merged, n_added)."""
    path = overrides_dir / f"{lang}.tsv"
    existing = _layer_entries(path, lang) if path.exists() else {}
    added = 0
    merged = dict(existing)
    for form, lemma in candidates.items():
        cform = canonicalize_token(form, lang)
        if " " in cform or not cform or cform in merged:
            continue
        merged[cform] = canonicalize_token(lemma, lang)
        added += 1
    return merged, added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="On a passing gate, update training/overrides/<lang>.tsv "
        "(default: write the candidate to training/output/ only).",
    )
    parser.add_argument("--epsilon", type=float, default=DEFAULT_EPSILON)
    args = parser.parse_args()
    lang = args.lang

    train_paths = discover_treebanks(lang, split="train")
    if not train_paths:
        sys.exit(f"no -ud-train split found for {lang!r}")
    candidates = resolve_overrides(*collect_candidates(train_paths, lang))

    # delta-only: an entry the baseline already reproduces is noise in a
    # reviewed file. Same composed baseline as the gate, so they can't drift.
    baseline = _compose_dictionary(lang, base="shipped")
    baseline_strategy = build_strategy(baseline)
    candidates = {
        form: lemma
        for form, lemma in candidates.items()
        if (baseline_strategy.get_lemma(form, lang) or form) != lemma
    }
    merged, n_added = merge_with_existing(candidates, lang)
    log.info(f"{lang}: {n_added} new entries over {len(merged) - n_added} existing")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{lang}.tsv"
    write_pairs(((lemma, form) for form, lemma in sorted(merged.items())), out_path)
    if not n_added:
        log.info(f"nothing to gate; candidate written to {out_path}")
        return

    candidate = _compose_dictionary(lang, base="shipped", overrides_dir=OUTPUT_DIR)
    if not report_results(gate(lang, baseline, candidate), args.epsilon):
        sys.exit(f"gate FAILED for {lang}; candidate left in {out_path} for review")
    if args.in_place:
        shutil.copy(out_path, OVERRIDES_DIR / f"{lang}.tsv")
        log.info(
            f"updated {OVERRIDES_DIR / f'{lang}.tsv'} -- rebuild the dictionary to ship"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
