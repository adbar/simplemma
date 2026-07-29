"""Eval release gate: assert a candidate dictionary doesn't regress accuracy
vs a baseline, on every available UD test treebank for the language, using
both token-level (frequency-weighted) and type-level (unweighted) accuracy.

Type-level matters because token-level alone can be fooled: a lever that
looks ~free on running text can still gut rare/tail-word coverage, which
token accuracy barely notices (frequency pruning is the textbook example).

`gate()` is the library entry point; the CLI is for manual spot-checks
against already-built lemma<TAB>form TSVs.

Usage: uv run python -m training.eval_gate <lang> <baseline.tsv> <candidate.tsv>
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from training.clean_wordlist import read_pairs
from training.eval_harness import (
    accuracy,
    build_strategy,
    gold_types,
    load_gold_tokens,
)
from training.ud_conllu import dataset_to_lang

log = logging.getLogger(__name__)

UD_SPLITS = Path(__file__).parent / "data" / "UD" / "splits"

# Tolerance for measurement noise, not a researched constant.
DEFAULT_EPSILON = 0.001


@dataclass
class TreebankResult:
    treebank: str
    baseline_token: float
    candidate_token: float
    baseline_type: float
    candidate_type: float
    n_tokens: int
    n_types: int

    @property
    def token_delta(self) -> float:
        return self.candidate_token - self.baseline_token

    @property
    def type_delta(self) -> float:
        return self.candidate_type - self.baseline_type

    def passed(self, epsilon: float = DEFAULT_EPSILON) -> bool:
        return self.token_delta >= -epsilon and self.type_delta >= -epsilon


def discover_treebanks(
    lang: str, split: str = "test", ud_splits: Path | None = None
) -> list[Path]:
    """Every *-ud-<split>.conllu file whose dataset belongs to `lang` (dataset
    name is `{code}_{treebank}`) -- multiple matches make the gate
    cross-treebank automatically."""
    suffix = f"-ud-{split}.conllu"
    return sorted(
        path
        for path in (ud_splits or UD_SPLITS).glob(f"*{suffix}")
        if dataset_to_lang(path.name.removesuffix(suffix)) == lang
    )


def gate(
    lang: str,
    baseline: dict[str, str],
    candidate: dict[str, str],
    ud_splits: Path | None = None,
) -> list[TreebankResult]:
    """Run token+type accuracy for baseline and candidate on every available
    test treebank for `lang`. Raises if none are found (a gate that silently
    checks nothing must not be mistaken for a gate that passed)."""
    treebanks = discover_treebanks(lang, ud_splits=ud_splits)
    if not treebanks:
        raise ValueError(f"no UD test treebank found for language {lang!r}")

    # build each strategy once (encoding is the costly part), reuse
    baseline_strategy = build_strategy(baseline)
    candidate_strategy = build_strategy(candidate)

    results = []
    for test_path in treebanks:
        gold_tokens = load_gold_tokens(test_path, lang)
        gold_type_pairs = gold_types(gold_tokens)  # strategy-independent; build once
        baseline_token, n_tokens = accuracy(baseline_strategy, lang, gold_tokens)
        candidate_token, _ = accuracy(candidate_strategy, lang, gold_tokens)
        baseline_type, n_types = accuracy(baseline_strategy, lang, gold_type_pairs)
        candidate_type, _ = accuracy(candidate_strategy, lang, gold_type_pairs)
        results.append(
            TreebankResult(
                treebank=test_path.stem,
                baseline_token=baseline_token,
                candidate_token=candidate_token,
                baseline_type=baseline_type,
                candidate_type=candidate_type,
                n_tokens=n_tokens,
                n_types=n_types,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lang")
    parser.add_argument("baseline_tsv", type=Path, help="lemma<TAB>form TSV")
    parser.add_argument("candidate_tsv", type=Path, help="lemma<TAB>form TSV")
    parser.add_argument("--epsilon", type=float, default=DEFAULT_EPSILON)
    args = parser.parse_args()

    baseline = read_pairs(args.baseline_tsv)
    candidate = read_pairs(args.candidate_tsv)
    results = gate(args.lang, baseline, candidate)

    for result in results:
        status = "PASS" if result.passed(args.epsilon) else "FAIL"
        log.info(
            f"[{status}] {result.treebank}: "
            f"token {result.baseline_token:.4f}->{result.candidate_token:.4f} "
            f"({result.token_delta:+.4f}, n={result.n_tokens}), "
            f"type {result.baseline_type:.4f}->{result.candidate_type:.4f} "
            f"({result.type_delta:+.4f}, n={result.n_types})"
        )

    if not all(result.passed(args.epsilon) for result in results):
        print(f"ERROR: eval gate FAILED for {args.lang}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
