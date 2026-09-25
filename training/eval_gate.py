"""Eval release gate: assert a candidate dictionary doesn't regress accuracy
vs a baseline, on every available UD treebank for the language -- each at its
most-held-out split (train, else dev, else test) -- using both token-level
(frequency-weighted) and type-level (unweighted) accuracy.

Also hosts the scoring primitives: the full `Lemmatizer` over a candidate
mapping, the same protocol `evaluate_simplemma` uses for the README numbers.

The gate is model selection, so it reads train, the only unpublished split;
train gets a delta's SIGN right but overstates its size (~1.22x) -- never
report or rank from it (sweep in training/README.rst). Type-level matters
because token-level alone misses gutted tail coverage. `split` is required
at every call site so none inherits one silently.

Library only: `gate()` + `report_results()` over in-memory dicts.
"""

import logging
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from simplemma import Lemmatizer
from simplemma.strategies import DefaultStrategy, DictionaryFactory
from training.ud_conllu import discover_treebanks, iter_word_tokens

log = logging.getLogger(__name__)

# Tolerance for measurement noise, not a researched constant.
DEFAULT_EPSILON = 0.001


class FixedDictionaryFactory(DictionaryFactory):
    """Serves one fixed str->str mapping as the dictionary for any language."""

    def __init__(self, mapping: Mapping[str, str]) -> None:
        self._mapping = mapping

    def get_dictionary(self, lang: str) -> Mapping[str, str]:
        return self._mapping


def build_lemmatizer(mapping: Mapping[str, str]) -> Lemmatizer:
    """The user-facing Lemmatizer over a fixed mapping."""
    return Lemmatizer(
        lemmatization_strategy=DefaultStrategy(
            dictionary_factory=FixedDictionaryFactory(mapping)
        )
    )


def load_gold_tokens(test_path: Path, lang: str) -> list[tuple[str, str]]:
    """(form, gold_lemma) pairs, parsed once; gold already canonicalized for
    `lang` by iter_word_tokens."""
    return [(form, token["lemma"]) for form, token in iter_word_tokens(test_path, lang)]


def gold_types(gold_tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """One (form, majority gold) pair per distinct form, for type-level
    accuracy (catches tail regressions token weighting hides)."""
    by_form: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for form, gold_lemma in gold_tokens:
        by_form[form][gold_lemma] += 1
    return [(form, counts.most_common(1)[0][0]) for form, counts in by_form.items()]


def accuracy(
    lemmatizer: Lemmatizer, lang: str, pairs: Iterable[tuple[str, str]]
) -> tuple[float, int]:
    """Fraction of (form, gold_lemma) pairs lemmatized to gold. Token- vs
    type-level is just which pairs you pass."""
    correct = 0
    total = 0
    for form, gold_lemma in pairs:
        correct += lemmatizer.lemmatize(form, lang) == gold_lemma
        total += 1
    return correct / total if total else 0.0, total


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


def gate(
    lang: str,
    baseline: dict[str, str],
    candidate: dict[str, str],
    ud_splits: Path | None = None,
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

    baseline_lemmatizer = build_lemmatizer(baseline)
    candidate_lemmatizer = build_lemmatizer(candidate)

    results = []
    for path in (treebanks[dataset] for dataset in sorted(treebanks)):
        gold_tokens = load_gold_tokens(path, lang)
        gold_type_pairs = gold_types(gold_tokens)
        baseline_token, n_tokens = accuracy(baseline_lemmatizer, lang, gold_tokens)
        candidate_token, _ = accuracy(candidate_lemmatizer, lang, gold_tokens)
        baseline_type, n_types = accuracy(baseline_lemmatizer, lang, gold_type_pairs)
        candidate_type, _ = accuracy(candidate_lemmatizer, lang, gold_type_pairs)
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
