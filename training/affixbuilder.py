"""
Measurement harness for `simplemma/strategies/affix_decomposition.py`'s
per-language config (the `AFFIX_LANGS` dict / `greedy_min_length`).

Method: sample (form, lemma) pairs from the dictionary and feed `form`
straight to `AffixDecompositionStrategy` -- the strategy never looks up the
full token, only its parts, so in-dict forms are a fair OOV simulation.
Candidates are first restricted to tokens the EARLIER chain stages (hyphen
removal, rules, prefix decomposition -- not dictionary lookup, deliberately
bypassed to simulate an unseen token) do not already resolve, since those
never reach affix decomposition in the real pipeline.

net% = (gain - harm) / n is the membership criterion:
  gain = fired & form != lemma & output == lemma  (decomposition helped)
  harm = fired & form == lemma & output != form    (decomposition hurt a citation form)

Usage: uv run python training/affixbuilder.py [lang ...]  (default: all languages)
"""

import random
from collections import Counter
from typing import cast

from simplemma.strategies.affix_decomposition import AffixDecompositionStrategy
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    DefaultDictionaryFactory,
)
from simplemma.strategies.dictionary_lookup import DictionaryLookupStrategy
from simplemma.strategies.hyphen_removal import HyphenRemovalStrategy
from simplemma.strategies.prefix_decomposition import PrefixDecompositionStrategy
from simplemma.strategies.rules import RulesStrategy

Pairs = list[tuple[str, str]]

SAMPLE_DEFAULT = 4000
SEED_DEFAULT = 7
MINCOMPLEN_DEFAULT = 4

FACTORY = DefaultDictionaryFactory()
_DICT_LOOKUP = DictionaryLookupStrategy(FACTORY)
_HYPHEN = HyphenRemovalStrategy(_DICT_LOOKUP)
_RULES = RulesStrategy()
_PREFIX = PrefixDecompositionStrategy(dictionary_lookup=_DICT_LOOKUP)
_STRAT = AffixDecompositionStrategy(True, _DICT_LOOKUP)


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def sample_pairs(
    lang: str,
    sample: int = SAMPLE_DEFAULT,
    seed: int = SEED_DEFAULT,
    capitalized: bool = False,
) -> Pairs:
    """Sample (form, lemma) pairs from `lang`'s dictionary; non-capitalized
    forms by default, capitalized-only with `capitalized=True` (relevant for
    noun-capitalizing languages like de, where compounds are capitalized)."""
    d = FACTORY.get_dictionary(lang)
    pairs = [(f, lemma) for f, lemma in d.items() if f[:1].isupper() == capitalized]
    if len(pairs) > sample:
        pairs = random.Random(seed).sample(pairs, sample)
    return pairs


def reaches_affix(token: str, lang: str) -> bool:
    """True if the real pipeline's earlier stages (hyphen/rules/prefix)
    leave `token` unresolved, so it would actually reach affix
    decomposition. Dictionary lookup is deliberately skipped here -- that's
    the OOV simulation itself."""
    return (
        _HYPHEN.get_lemma(token, lang) is None
        and _RULES.get_lemma(token, lang) is None
        and _PREFIX.get_lemma(token, lang) is None
    )


def _filter_reachable(pairs: Pairs, lang: str, min_length: int) -> Pairs:
    return [
        (f, lemma)
        for f, lemma in pairs
        if len(f) > min_length and reaches_affix(f, lang)
    ]


def measure(
    lang: str,
    max_affix_len: int,
    min_length: int,
    pairs: Pairs | None = None,
    min_complem_len: int = MINCOMPLEN_DEFAULT,
) -> dict[str, object]:
    """Net benefit of affix decomposition for `lang` at a given
    (max_affix_len, min_length). Calls the two sub-strategies directly
    (bypassing `get_lemma`'s static config lookup) so any parameter
    combination can be swept, not just the currently shipped one.

    `net_pct` divides by the tokens that PASS the min_length gate, so it is
    only comparable across configs sharing one min_length (a higher gate
    keeps an easier population). `net_full_pct` divides by the whole sample
    (gated-out tokens pass through unchanged: 0 gain, 0 harm) and is the
    fair number for comparing min_length values."""
    pairs = pairs if pairs is not None else sample_pairs(lang)
    n_full = len(pairs)
    pairs = _filter_reachable(pairs, lang, min_length)
    n = len(pairs)
    fired = gain = harm = changed = changed_ok = 0
    for f, lemma in pairs:
        p = _STRAT._affix_decomposition(
            f, lang, max_affix_len, min_complem_len
        ) or _STRAT._suffix_decomposition(f, lang, min_complem_len)
        if p is None:
            continue
        fired += 1
        if p != f:
            changed += 1
            changed_ok += p == lemma
        if f != lemma and p == lemma:
            gain += 1
        elif f == lemma and p != f:
            harm += 1
    return {
        "lang": lang,
        "n": n,
        "fired": fired,
        "gain": gain,
        "harm": harm,
        "net_pct": 100 * (gain - harm) / n if n else 0.0,
        "net_full_pct": 100 * (gain - harm) / n_full if n_full else 0.0,
        # correctness of VISIBLE changes -- wrong-changed inflected forms are
        # exact-match-neutral (excluded from net) but user-visible garbage
        "changed": changed,
        "changed_prec_pct": 100 * changed_ok / changed if changed else 0.0,
    }


def sweep(
    lang: str,
    affix_lens: tuple[int, ...] = (2, 3, 4, 5, 6),
    min_lengths: tuple[int, ...] = (5, 6, 7, 8),
    pairs: Pairs | None = None,
) -> list[dict[str, object]]:
    "All (max_affix_len, min_length) combinations for `lang`, best net_full% first."
    pairs = pairs if pairs is not None else sample_pairs(lang)
    rows = [
        {
            **measure(lang, affix_len, min_len, pairs=pairs),
            "max_affix_len": affix_len,
            "min_length": min_len,
        }
        for affix_len in affix_lens
        for min_len in min_lengths
    ]
    rows.sort(key=lambda r: cast(float, r["net_full_pct"]), reverse=True)
    return rows


def sub_strategy_breakdown(
    lang: str,
    max_affix_len: int,
    min_length: int,
    pairs: Pairs | None = None,
    min_complem_len: int = MINCOMPLEN_DEFAULT,
) -> dict[str, object]:
    "How much `_suffix_decomposition` adds beyond `_affix_decomposition` alone."
    pairs = pairs if pairs is not None else sample_pairs(lang)
    pairs = _filter_reachable(pairs, lang, min_length)
    affix_fired = affix_ok = 0
    suffix_only_fired = suffix_only_ok = 0
    for f, lemma in pairs:
        pa = _STRAT._affix_decomposition(f, lang, max_affix_len, min_complem_len)
        if pa is not None:
            affix_fired += 1
            affix_ok += pa == lemma
            continue
        ps = _STRAT._suffix_decomposition(f, lang, min_complem_len)
        if ps is not None:
            suffix_only_fired += 1
            suffix_only_ok += ps == lemma
    total_fired = affix_fired + suffix_only_fired
    return {
        "lang": lang,
        "n": len(pairs),
        "affix_fired": affix_fired,
        "affix_prec": 100 * affix_ok / affix_fired if affix_fired else 0.0,
        "suffix_only_fired": suffix_only_fired,
        "suffix_only_prec": 100 * suffix_only_ok / suffix_only_fired
        if suffix_only_fired
        else 0.0,
        "suffix_only_share_pct": 100 * suffix_only_fired / total_fired
        if total_fired
        else 0.0,
    }


def classify_declines(
    lang: str,
    max_affix_len: int,
    min_length: int,
    pairs: Pairs | None = None,
    min_complem_len: int = MINCOMPLEN_DEFAULT,
    limit: int = 20,
) -> dict[str, object]:
    """For inflected forms (form != lemma) reaching affix decomposition that
    get None, classify why: no truncation of the token is itself a dict
    entry ('no_part1' -- the stem never surfaces as a standalone word,
    e.g. stem alternation), the correct stem boundary IS a dict entry but
    no valid part2 completed it ('part1_ok_part2_failed'), or some OTHER
    boundary matched first, pre-empting the correct one ('wrong_split_taken')."""
    d = FACTORY.get_dictionary(lang)
    pairs = pairs if pairs is not None else sample_pairs(lang)
    pairs = [
        (f, lemma)
        for f, lemma in pairs
        if f != lemma and len(f) > min_length and reaches_affix(f, lang)
    ]
    counts: Counter[str] = Counter()
    examples: dict[str, Pairs] = {}
    for f, lemma in pairs:
        p = _STRAT._affix_decomposition(
            f, lang, max_affix_len, min_complem_len
        ) or _STRAT._suffix_decomposition(f, lang, min_complem_len)
        if p is not None:
            counts["resolved"] += 1
            continue
        cp = _common_prefix_len(f, lemma)
        stem = f[:cp]
        correct_boundary_has_part1 = cp >= 2 and d.get(stem) is not None
        any_part1_hit = any(
            d.get(f[:-count]) is not None
            for count in range(1, len(f) - min_complem_len + 1)
        )
        if not any_part1_hit:
            key = "no_part1"
        elif correct_boundary_has_part1:
            key = "part1_ok_part2_failed"
        else:
            key = "wrong_split_taken"
        counts[key] += 1
        examples.setdefault(key, [])
        if len(examples[key]) < limit:
            examples[key].append((f, lemma))
    return {"lang": lang, "n": len(pairs), "counts": dict(counts), "examples": examples}


if __name__ == "__main__":
    import sys

    langs = sys.argv[1:] or sorted(SUPPORTED_LANGUAGES)
    for language in langs:
        best = sweep(language)[0]
        print(
            f"{language}: best net_full={best['net_full_pct']:.1f}% "
            f"(max_affix_len={best['max_affix_len']}, min_length={best['min_length']}) "
            f"gain={best['gain']} harm={best['harm']} fired={best['fired']}/{best['n']}"
        )
