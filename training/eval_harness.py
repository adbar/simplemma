"""Shared evaluation helpers: run the real DefaultStrategy chain over an
arbitrary in-memory dictionary and score it against a UD treebank. Used by
wikidata_lexemes.py's prune functions, eval_gate.py, and validate_* scripts,
so the eval protocol lives in one place.

Bare strategy with identity fallback -- the dictionary-quality gate protocol.
Distinct from `evaluate_simplemma`, which scores the full user-facing
Lemmatizer (lowercase fallback) for the published README numbers.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from simplemma.strategies import DefaultStrategy, DictionaryFactory
from simplemma.strategies.dictionaries.dictionary_factory import MappingStrToByteString
from training.ud_conllu import iter_word_tokens


class FixedDictionaryFactory(DictionaryFactory):
    """Serves one fixed str->str mapping as the dictionary for any language,
    so DefaultStrategy can run over an arbitrary candidate dict."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self._wrapped = MappingStrToByteString(
            {k.encode(): v.encode() for k, v in mapping.items()}
        )

    def get_dictionary(self, lang: str) -> MappingStrToByteString:
        return self._wrapped


def _iter_gold_tokens(test_path: Path) -> Iterator[tuple[str, str]]:
    """(form, gold_lemma) for a test treebank, UD-eval convention applied."""
    for form, token in iter_word_tokens(test_path):
        yield form, token["lemma"]


def load_gold_tokens(test_path: Path) -> list[tuple[str, str]]:
    """Materialize a treebank's gold tokens once, so multiple strategies can
    be scored without re-parsing the conllu file per call."""
    return list(_iter_gold_tokens(test_path))


def build_strategy(mapping: dict[str, str]) -> DefaultStrategy:
    """The real DefaultStrategy chain over a fixed candidate mapping. Encodes
    once -- reuse across treebanks/metrics rather than rebuilding per score."""
    return DefaultStrategy(dictionary_factory=FixedDictionaryFactory(mapping))


def accuracy(
    strategy: DefaultStrategy, lang: str, pairs: Iterable[tuple[str, str]]
) -> tuple[float, int]:
    """Fraction of (form, gold_lemma) pairs lemmatized to gold (identity
    fallback on a miss). Token- vs type-level is just which pairs you pass."""
    correct = 0
    total = 0
    for form, gold_lemma in pairs:
        prediction = strategy.get_lemma(form, lang) or form
        correct += prediction == gold_lemma
        total += 1
    return correct / total if total else 0.0, total


def gold_types(gold_tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Reduce occurrence pairs to one (form, majority-gold-lemma) pair per
    distinct form, for type-level (unweighted) accuracy -- guards against
    token-level frequency weighting hiding a rare/tail-word regression.

    Strategy-independent: build once per treebank and reuse across
    strategies."""
    by_form: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for form, gold_lemma in gold_tokens:
        by_form[form][gold_lemma] += 1
    return [(form, counts.most_common(1)[0][0]) for form, counts in by_form.items()]
