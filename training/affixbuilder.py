"""
Measurement harness for `AFFIX_LANGS` / `greedy_min_length` in
`simplemma/strategies/affix_decomposition.py`.

Feeds dictionary `form`s to `AffixDecompositionStrategy` (which only looks up
their parts, so in-dict forms are a fair OOV simulation), restricted to tokens
the earlier stages (hyphen/rules/prefix, NOT dict lookup) don't already
resolve. Membership criterion net_full% = (gain - harm) / sample_size, where
gain = form!=lemma & output==lemma, harm = form==lemma & output!=form.

Usage: uv run python training/affixbuilder.py [lang ...]  (default: all)
"""

import random
from typing import cast

# imported, not mirrored: the harness must track the runtime's remainder floor
from simplemma.strategies.affix_decomposition import (
    MINCOMPLEN,
    AffixDecompositionStrategy,
)
from simplemma.strategies.dictionaries.dictionary_factory import (
    SUPPORTED_LANGUAGES,
    DEFAULT_DICTIONARY_FACTORY,
)
from simplemma.strategies.dictionary_lookup import DictionaryLookupStrategy
from simplemma.strategies.hyphen_removal import HyphenRemovalStrategy
from simplemma.strategies.prefix_decomposition import PrefixDecompositionStrategy
from simplemma.strategies.rules import RulesStrategy

Pairs = list[tuple[str, str]]

SAMPLE_DEFAULT = 4000
SEED_DEFAULT = 7

FACTORY = DEFAULT_DICTIONARY_FACTORY  # shared process-wide cache
_DICT_LOOKUP = DictionaryLookupStrategy(FACTORY)
_HYPHEN = HyphenRemovalStrategy(_DICT_LOOKUP)
_RULES = RulesStrategy()
_PREFIX = PrefixDecompositionStrategy(dictionary_lookup=_DICT_LOOKUP)
_STRAT = AffixDecompositionStrategy(True, _DICT_LOOKUP)


def _pct(num: int, den: int) -> float:
    return 100 * num / den if den else 0.0


def sample_pairs(
    lang: str,
    sample: int = SAMPLE_DEFAULT,
    seed: int = SEED_DEFAULT,
) -> Pairs:
    """Sample lowercase (form, lemma) pairs (capitalized = proper nouns /
    compounds, a separate population affix decomposition mishandles)."""
    d = FACTORY.get_dictionary(lang)
    pairs = [(f, lemma) for f, lemma in d.items() if not f[:1].isupper()]
    if len(pairs) > sample:
        pairs = random.Random(seed).sample(pairs, sample)
    return pairs


def reaches_affix(token: str, lang: str) -> bool:
    """True if the earlier stages (hyphen/rules/prefix) leave `token`
    unresolved -- dict lookup skipped, that IS the OOV simulation."""
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
) -> dict[str, object]:
    """Net benefit for `lang` at (max_affix_len, min_length). Calls the
    sub-strategies directly so any parameter combo can be swept. net_full_pct
    divides by the whole sample (gated-out tokens = 0 gain/harm), the fair
    cross-min_length number."""
    pairs = pairs if pairs is not None else sample_pairs(lang)
    n_full = len(pairs)
    pairs = _filter_reachable(pairs, lang, min_length)
    n = len(pairs)
    fired = gain = harm = changed = changed_ok = 0
    for f, lemma in pairs:
        p = _STRAT._affix_decomposition(
            f, lang, max_affix_len, MINCOMPLEN
        ) or _STRAT._suffix_decomposition(f, lang, MINCOMPLEN)
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
        "net_full_pct": _pct(gain - harm, n_full),
        # precision of visible changes (net-neutral, but user-visible garbage)
        "changed": changed,
        "changed_prec_pct": _pct(changed_ok, changed),
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
