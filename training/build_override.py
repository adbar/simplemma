"""Mine a reviewed override lexicon (form -> lemma) for one language from its
UD train splits, and gate it end-to-end before it can ship.

Pool every -ud-train split; keep a form's majority lemma when the pooled
evidence clears its POS-class bar AND every often-attesting treebank agrees
(the per-treebank veto removes convention splits: la "esse", fr "se" -> soi).
Every threshold-clearing form is kept -- the file is a pure function of the
UD data plus review; already-reproduced entries are only counted in the log.

Usage: uv run python -m training.build_override <lang> [--in-place]

The merged candidate file (existing overrides + mined additions) is gated
with eval_gate on every train treebank; output goes to training/output/
unless --in-place updates training/overrides/<lang>.tsv. Shipping the effect
still requires a dictionary rebuild (python -m training.dictionary_builder
--in-place).
"""

import argparse
import logging
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from simplemma.utils import canonicalize_token, normalize_token
from training.clean_wordlist import pair_violation, write_pairs
from training.dictionary_builder import (
    OVERRIDES_DIR,
    _compose_base,
    _compose_from_base,
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
    attesting treebank disagrees. Ties never depend on insertion order:
    majority by (count, lemma), a POS tie takes the stricter open-class
    bar, a veto needs a lemma strictly beating the pooled winner."""
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
    """Existing reviewed entries win their forms; candidates are folded to
    the runtime key space (canon + NFC, matching read_pairs) and skipped on
    any pair_violation or spaced field, so a written candidate file can
    never fail the read side. Returns (merged, n_added). grc/he/ar
    candidates can fold to one canonical key: first lemma wins, with a
    WARNING (_layer_entries raises on this in a hand-edited file)."""
    path = (overrides_dir or OVERRIDES_DIR) / f"{lang}.tsv"
    existing = _layer_entries(path, lang) if path.exists() else {}
    added = 0
    merged = dict(existing)
    for form, lemma in candidates.items():
        cform = normalize_token(canonicalize_token(form, lang))
        clemma = normalize_token(canonicalize_token(lemma, lang))
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

    # Redundancy is reported, never filtered: the committed file stays a pure
    # function of UD + review. Same composed baseline as the gate below; the
    # base is composed once, then layered with each override set.
    base = _compose_base(lang)
    baseline = _compose_from_base(base, lang)
    baseline_strategy = build_strategy(baseline)
    redundant = sum(
        1
        for form, lemma in candidates.items()
        if (baseline_strategy.get_lemma(form, lang) or form) == lemma
    )
    merged, n_added = merge_with_existing(candidates, lang)
    log.info(
        f"{lang}: {n_added} new entries over {len(merged) - n_added} existing; "
        f"{redundant}/{len(candidates)} mined forms already reproduced by the baseline"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{lang}.tsv"
    write_pairs(((lemma, form) for form, lemma in sorted(merged.items())), out_path)
    if not n_added:
        log.info(f"nothing to gate; candidate written to {out_path}")
        return

    candidate = _compose_from_base(base, lang, overrides_dir=OUTPUT_DIR)
    if not report_results(
        gate(lang, baseline, candidate, baseline_strategy=baseline_strategy),
        args.epsilon,
    ):
        sys.exit(f"gate FAILED for {lang}; candidate left in {out_path} for review")
    if args.in_place:
        shutil.copy(out_path, OVERRIDES_DIR / f"{lang}.tsv")
        log.info(
            f"updated {OVERRIDES_DIR / f'{lang}.tsv'} -- rebuild the dictionary to ship"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
