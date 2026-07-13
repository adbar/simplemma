"""
Shared evaluation helpers for the v2.0 dictionary work: run the real
DefaultStrategy chain over an arbitrary in-memory dictionary and score it
against a UD treebank. Used by the prune functions in wikidata_lexemes.py, by
eval_gate.py, and by the validate_* scripts, so the eval protocol lives in
exactly one place.
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
    """Materialize a treebank's gold tokens once, so score_token/score_type can
    each score multiple strategies (e.g. a gate's baseline + candidate) without
    re-parsing the conllu file per call."""
    return list(_iter_gold_tokens(test_path))


def build_strategy(mapping: dict[str, str]) -> DefaultStrategy:
    """The real DefaultStrategy chain over a fixed candidate mapping. Encodes
    the whole mapping once -- build per mapping and reuse across treebanks and
    metrics rather than rebuilding per score."""
    return DefaultStrategy(dictionary_factory=FixedDictionaryFactory(mapping))


def _accuracy(
    strategy: DefaultStrategy, lang: str, pairs: Iterable[tuple[str, str]]
) -> tuple[float, int]:
    """Fraction of (form, gold_lemma) pairs the strategy lemmatizes to gold
    (identity fallback on a miss). Returns (accuracy, count)."""
    correct = 0
    total = 0
    for form, gold_lemma in pairs:
        prediction = strategy.get_lemma(form, lang) or form
        correct += prediction == gold_lemma
        total += 1
    return correct / total if total else 0.0, total


def score_token(
    strategy: DefaultStrategy, lang: str, gold_tokens: list[tuple[str, str]]
) -> tuple[float, int]:
    """Token-level (frequency-weighted) accuracy: each occurrence in the corpus
    counts once, so common forms dominate. Returns (accuracy, token_count)."""
    return _accuracy(strategy, lang, gold_tokens)


def score_type(
    strategy: DefaultStrategy, lang: str, gold_tokens: list[tuple[str, str]]
) -> tuple[float, int]:
    """Type-level (unweighted) accuracy: one vote per DISTINCT form regardless
    of how often it occurs (majority gold lemma if a form has more than one).
    Guards against the token-level metric's frequency weighting hiding a
    rare/tail-word regression (frequency pruning can look "free" on tokens
    while gutting tail coverage). Returns (accuracy, type_count)."""
    gold_by_form: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for form, gold_lemma in gold_tokens:
        gold_by_form[form][gold_lemma] += 1
    majority = (
        (form, counts.most_common(1)[0][0]) for form, counts in gold_by_form.items()
    )
    return _accuracy(strategy, lang, majority)


def load_lemma_form_tsv(path: Path) -> dict[str, str]:
    """Load a lemma<TAB>form file (the pickler/override/fill convention) into
    a runtime form->lemma mapping. Blank lines are skipped; any other line
    without exactly one tab raises, naming the file and line number."""
    mapping = {}
    with open(path, encoding="utf-8") as filehandle:
        for line_no, line in enumerate(filehandle, start=1):
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            parts = stripped.split("\t")
            if len(parts) != 2:
                raise ValueError(
                    f"{path}:{line_no}: expected 'lemma<TAB>form', got {stripped!r}"
                )
            lemma, form = parts
            mapping[form] = lemma
    return mapping
