"""Eval release gate: assert a candidate dictionary doesn't regress accuracy
vs a baseline, on every available UD treebank for the language -- each at its
most-held-out split (train, else dev, else test) -- using both token-level
(frequency-weighted) and type-level (unweighted) accuracy.

The gate is model selection, so it reads train, the only unpublished split;
train gets a delta's SIGN right but overstates its size (~1.22x) -- never
report or rank from it (sweep in training/README.rst). Type-level matters
because token-level alone misses gutted tail coverage. `split` is required
at every call site so none inherits one silently.

Usage: uv run python -m training.eval_gate <lang> <baseline.tsv> <candidate.tsv>
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from simplemma.strategies import DefaultStrategy
from training.clean_wordlist import read_pairs
from training.eval_harness import (
    accuracy,
    build_strategy,
    gold_types,
    load_gold_tokens,
)
from training.ud_conllu import UD_SPLITS, dataset_to_lang

log = logging.getLogger(__name__)

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
    lang: str, split: str, ud_splits: Path | None = None
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
    baseline_strategy: DefaultStrategy | None = None,
) -> list[TreebankResult]:
    """Token+type accuracy for baseline and candidate on every treebank for
    `lang`, each at its most-held-out split -- resolved per TREEBANK, so
    test-only *_pud siblings keep gate coverage. Raises when no treebank is
    found (a gate that checks nothing must not look passed); a treebank gated
    on dev/test logs a WARNING (that figure is selected, not held out)."""
    treebanks: dict[str, Path] = {}
    for split in ("train", "dev", "test"):
        for path in discover_treebanks(lang, split, ud_splits=ud_splits):
            dataset = path.name.split("-ud-", 1)[0]
            if dataset in treebanks:
                continue
            treebanks[dataset] = path
            if split != "train":
                log.warning(
                    "%s has no UD train split: gating on %s, which is a "
                    "REPORTED split -- its published accuracy is not held out",
                    dataset,
                    split.upper(),
                )
    if not treebanks:
        raise ValueError(f"no UD treebank of any split found for language {lang!r}")

    # build each strategy once (encoding is the costly part), reuse; a caller
    # that already built the baseline strategy passes it in instead
    if baseline_strategy is None:
        baseline_strategy = build_strategy(baseline)
    candidate_strategy = build_strategy(candidate)

    results = []
    for path in (treebanks[dataset] for dataset in sorted(treebanks)):
        gold_tokens = load_gold_tokens(path, lang)
        gold_type_pairs = gold_types(gold_tokens)  # strategy-independent; build once
        baseline_token, n_tokens = accuracy(baseline_strategy, lang, gold_tokens)
        candidate_token, _ = accuracy(candidate_strategy, lang, gold_tokens)
        baseline_type, n_types = accuracy(baseline_strategy, lang, gold_type_pairs)
        candidate_type, _ = accuracy(candidate_strategy, lang, gold_type_pairs)
        results.append(
            TreebankResult(
                treebank=path.stem,
                baseline_token=baseline_token,
                candidate_token=candidate_token,
                baseline_type=baseline_type,
                candidate_type=candidate_type,
                n_tokens=n_tokens,
                n_types=n_types,
            )
        )
    return results


def report_results(
    results: list[TreebankResult], epsilon: float = DEFAULT_EPSILON
) -> bool:
    """Log one PASS/FAIL line per treebank; True when every treebank passed."""
    for result in results:
        status = "PASS" if result.passed(epsilon) else "FAIL"
        log.info(
            f"[{status}] {result.treebank}: "
            f"token {result.baseline_token:.4f}->{result.candidate_token:.4f} "
            f"({result.token_delta:+.4f}, n={result.n_tokens}), "
            f"type {result.baseline_type:.4f}->{result.candidate_type:.4f} "
            f"({result.type_delta:+.4f}, n={result.n_types})"
        )
    return all(result.passed(epsilon) for result in results)


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

    if not report_results(results, args.epsilon):
        print(f"ERROR: eval gate FAILED for {args.lang}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
