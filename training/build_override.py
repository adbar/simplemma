"""
Derive a closed-class override lexicon (form -> lemma) from a UD train
split. Closed classes (pronouns, determiners, adpositions, conjunctions,
auxiliaries, particles) are the one place Kaikki/Wiktionary is
systematically thin (described in prose, not inflection tables), and
they're convention-stable across treebanks/corpora -- unlike content-word
lemmatization, which varies by annotation convention and does NOT transfer
safely.

This is the "closed_safe" methodology from the original research: mine a
form's majority lemma from train data, keep it only if the train data
itself agrees with that majority strongly and often enough. The shipped
artifact is meant to be reviewed, not auto-applied blind -- this script
produces the CANDIDATE list; eval_gate.py checks it actually helps on
held-out test data (every treebank for the language, token + type).
"""

import argparse
import logging
from collections import Counter, defaultdict
from pathlib import Path

from training.ud_conllu import iter_word_tokens

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CLOSED_CLASS_POS = frozenset({"PRON", "DET", "ADP", "CCONJ", "SCONJ", "AUX", "PART"})


def collect_candidates(train_path: Path) -> dict[str, Counter[str]]:
    """form -> Counter(lemma -> occurrence count), closed-class tokens only."""
    candidates: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for form, token in iter_word_tokens(train_path):
        if token["upos"] in CLOSED_CLASS_POS:
            candidates[form][token["lemma"]] += 1
    return dict(candidates)


def resolve_overrides(
    candidates: dict[str, Counter[str]],
    min_count: int = 3,
    min_agreement: float = 0.90,
) -> tuple[dict[str, str], dict[str, int]]:
    """Keep a form's majority lemma only if train data itself agrees with it
    strongly (>= min_agreement) and often (>= min_count) enough."""
    overrides = {}
    dropped_low_count = 0
    dropped_low_agreement = 0
    for form, counts in candidates.items():
        total = sum(counts.values())
        if total < min_count:
            dropped_low_count += 1
            continue
        lemma, count = counts.most_common(1)[0]
        agreement = count / total
        if agreement < min_agreement:
            dropped_low_agreement += 1
            continue
        overrides[form] = lemma
    stats = {
        "candidate_forms": len(candidates),
        "kept": len(overrides),
        "dropped_low_count": dropped_low_count,
        "dropped_low_agreement": dropped_low_agreement,
    }
    return overrides, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang")
    parser.add_argument("train_conllu", type=Path)
    parser.add_argument("output_tsv", type=Path)
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--min-agreement", type=float, default=0.90)
    args = parser.parse_args()

    candidates = collect_candidates(args.train_conllu)
    overrides, stats = resolve_overrides(candidates, args.min_count, args.min_agreement)
    log.info(f"{args.lang}: {stats}")

    with open(args.output_tsv, "w", encoding="utf-8") as filehandle:
        for form, lemma in sorted(overrides.items()):
            filehandle.write(f"{lemma}\t{form}\n")
    log.info(f"Wrote {len(overrides)} entries to {args.output_tsv}")


if __name__ == "__main__":
    main()
