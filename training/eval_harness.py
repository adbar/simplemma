"""Shared evaluation helpers: run the real DefaultStrategy chain over an
arbitrary in-memory dictionary and score it against a UD treebank. Used by
eval_gate.py, build_override.py and wikidata_lexemes.py's prune functions,
so the eval protocol lives in one place.

Bare strategy with identity fallback -- the dictionary-quality gate protocol.
Distinct from `evaluate_simplemma`, which scores the full user-facing
Lemmatizer (lowercase fallback) for the published README numbers.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from conllu import parse_incr

import simplemma.strategies.clitic_decomposition as clitic_decomposition
import simplemma.strategies.defaultprefixes as defaultprefixes
import simplemma.utils as simplemma_utils
from simplemma.strategies import DefaultStrategy, DictionaryFactory
from simplemma.strategies.dictionaries.dictionary_factory import MappingStrToByteString
from training.ud_conllu import (  # _strip_mwt_artifact: private, sibling module
    CONTENT_POS,
    _strip_mwt_artifact,
    canon_lemma,
    iter_word_tokens,
    iter_word_tokens_in_sentences,
)


class FixedDictionaryFactory(DictionaryFactory):
    """Serves one fixed str->str mapping as the dictionary for any language,
    so DefaultStrategy can run over an arbitrary candidate dict."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self._wrapped = MappingStrToByteString(
            {k.encode(): v.encode() for k, v in mapping.items()}
        )

    def get_dictionary(self, lang: str) -> MappingStrToByteString:
        return self._wrapped


def load_gold_tokens(test_path: Path, lang: str) -> list[tuple[str, str]]:
    """Materialize a treebank's (form, gold_lemma) pairs once, so multiple
    strategies can be scored without re-parsing the conllu file per call. The
    gold lemma is already canonicalized for `lang` by iter_word_tokens (a
    no-op outside _CANON_TABLES): e.g. PADT's vocalized gold is compared in
    the dict's own unvocalized key space."""
    return [(form, token["lemma"]) for form, token in iter_word_tokens(test_path, lang)]


def iter_real_word_tokens(test_path: Path, lang: str) -> Iterator[tuple[str, str]]:
    """(surface_form, gold_lemma) treating each REAL orthographic word as one
    input, unlike `iter_word_tokens`'s per-UD-sub-token protocol. A fused MWT
    span (he/ar proclitic+article glued onto a host word, e.g. he "שיכולת",
    ar "والكتاب") never occurs pre-split in real text -- simplemma's
    tokenizer receives it as ONE token -- so it's yielded as its own whole
    surface form, scored against its CONTENT sub-token's gold lemma
    (CONTENT_POS; the span's last sub-token if none qualify). This is the
    protocol that exposed the ~28pp he UD-vs-real-world gap: a language
    whose script fuses closed-class particles onto content words will always
    score higher under the standard per-sub-token protocol than in practice.
    Gold is canonicalized for `lang` (a no-op outside _CANON_TABLES)."""
    with open(test_path, encoding="utf-8") as filehandle:
        for tokens in parse_incr(filehandle):
            by_id = {t["id"]: t for t in tokens}
            span_ranges: set[int] = set()
            for t in tokens:
                tid = t["id"]
                if not (isinstance(tid, tuple) and tid[1] == "-"):
                    continue
                lo, hi = tid[0], tid[2]
                subs = [by_id[i] for i in range(lo, hi + 1) if i in by_id]
                span_ranges.update(range(lo, hi + 1))
                content = [
                    s for s in subs if s["upos"] in CONTENT_POS and s["lemma"] != "_"
                ]
                pick = content or subs
                if pick and pick[-1]["lemma"] != "_":
                    # span sub-tokens are read straight from by_id, so apply
                    # the shared gold transform here (the sentence iterator
                    # below only touches the non-span tokens it yields).
                    lemma = canon_lemma(pick[-1]["lemma"], pick[-1]["form"], lang)
                    yield _strip_mwt_artifact(t["form"]), lemma
            for form, token in iter_word_tokens_in_sentences([tokens], lang):
                if token["id"] not in span_ranges:
                    yield form, token["lemma"]


def build_strategy(mapping: dict[str, str]) -> DefaultStrategy:
    """The real DefaultStrategy chain over a fixed candidate mapping. Encodes
    once -- reuse across treebanks/metrics rather than rebuilding per score."""
    return DefaultStrategy(dictionary_factory=FixedDictionaryFactory(mapping))


@contextmanager
def mechanism_disabled(mechanism: str, lang: str) -> Iterator[None]:
    """Temporarily remove `lang` from one lemmatization mechanism (prefix /
    clitic / canon) for a held-out A/B, restoring on exit. Mutates the dict
    the RUNTIME actually reads for `mechanism` -- NOT a source of truth a
    derived structure shadows. Getting that target wrong gives a silent
    false +0.00pp, which happened TWICE this arc:
      - "prefix": DEFAULT_KNOWN_PREFIXES is bound once as PrefixDecomposition's
        default arg, so reassigning the module name is invisible -- must mutate
        this object in place.
      - "clitic": CLITIC_LANGS is the source, but the lookup reads the
        precomputed _CLITIC_SUFFIXES cache -- mutating CLITIC_LANGS never
        touches it.
      - "canon": TWO runtime readers -- canonicalize_token reads _CANON_TABLES,
        and clitic_decomposition resolves the module global CANON_LANGS (a
        frozenset snapshot) on each call. Popping _CANON_TABLES alone leaves
        that gate active, so narrow CANON_LANGS too.
    RAISES if `lang` isn't in the target -- a disable that changes nothing
    would silently measure the same config twice (the false-+0.00pp trap)."""
    targets: dict[str, dict[Any, Any]] = {
        "prefix": defaultprefixes.DEFAULT_KNOWN_PREFIXES,
        "clitic": clitic_decomposition._CLITIC_SUFFIXES,
        "canon": simplemma_utils._CANON_TABLES,
    }
    if mechanism not in targets:
        raise ValueError(f"unknown mechanism {mechanism!r}, expected {sorted(targets)}")
    target = targets[mechanism]
    if lang not in target:
        raise KeyError(
            f"{lang!r} not in the {mechanism!r} table -- nothing to disable "
            f"(a no-op A/B would falsely read as zero effect)"
        )
    saved = target.pop(lang)
    if mechanism == "canon":
        # CANON_LANGS is a snapshot of _CANON_TABLES re-imported (not owned) by
        # clitic_decomposition -- re-derive that module's own binding after
        # mutating the source table (and again after restoring it below).
        clitic_decomposition.CANON_LANGS = frozenset(simplemma_utils._CANON_TABLES)  # type: ignore[attr-defined]
    try:
        yield
    finally:
        target[lang] = saved
        if mechanism == "canon":
            clitic_decomposition.CANON_LANGS = frozenset(simplemma_utils._CANON_TABLES)  # type: ignore[attr-defined]


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
