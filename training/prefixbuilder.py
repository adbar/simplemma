"""
Mining/analysis tool that generates prefix-stripping candidates for
`simplemma/strategies/defaultprefixes/` from the shipped dictionaries --
a hypothesis generator, never evidence (see training/data/affix_eval/,
whose central finding is that in-dict measurement has ~0% hit rate for
sign on affix/prefix decisions). A candidate must still clear the same UD
tune/confirm gate as de/ru (training/data/affix_eval/scripts/
prefix_audit.py) before being added to a shipped list.

For every dictionary entry (form, lemma) and every prefix length where a
split leaves a plausible remainder (>=4 chars, mirroring
affix_decomposition.MINCOMPLEN) that is ITSELF a dictionary entry, check
whether lemma(form) == prefix + lemma(remainder). Group by prefix string,
count hits/misses. A high-precision, high-support prefix is worth an
actual UD gate run. A high identity-miss share (misses where the gold
lemma is the form itself) names the "za"/"zu" pattern found there:
prefix+remainder is often itself a fixed lexical item (lexicalization),
not a live derivation -- exactly the failure mode that made those two
entries net-harmful despite decent raw precision.

Usage: uv run python training/prefixbuilder.py <lang> [min_len] [support_min]
"""

import sys
from collections import Counter

from simplemma.strategies.dictionaries.dictionary_factory import (
    DefaultDictionaryFactory,
)

FACTORY = DefaultDictionaryFactory()
MIN_LEN_DEFAULT = 6  # shortest word considered for a prefix split
SUPPORT_MIN_DEFAULT = 30
PREFIX_LENS = range(2, 7)
MIN_REMAINDER = 4  # mirrors affix_decomposition.MINCOMPLEN


def mine(
    lang: str, min_len: int = MIN_LEN_DEFAULT
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    """hits/misses/identity_misses per candidate prefix string."""
    dictionary = FACTORY.get_dictionary(lang)
    hits: Counter[str] = Counter()
    misses: Counter[str] = Counter()
    identity_misses: Counter[str] = Counter()
    for form, lemma in dictionary.items():
        if not form.isalpha() or not form.islower() or len(form) < min_len:
            continue
        for plen in PREFIX_LENS:
            if len(form) - plen < MIN_REMAINDER:
                break
            prefix, remainder = form[:plen], form[plen:]
            remainder_lemma = dictionary.get(remainder)
            if remainder_lemma is None:
                continue
            if prefix + remainder_lemma == lemma:
                hits[prefix] += 1
            else:
                misses[prefix] += 1
                if lemma == form:
                    identity_misses[prefix] += 1
    return hits, misses, identity_misses


def report(
    lang: str,
    min_len: int = MIN_LEN_DEFAULT,
    support_min: int = SUPPORT_MIN_DEFAULT,
    watch: tuple[str, ...] = (),
) -> None:
    """Print the ranked candidate table; `watch` forces specific prefixes
    into the printout even if they fall below support_min (for
    calibration against a known-rejected entry)."""
    hits, misses, identity_misses = mine(lang, min_len)
    prefixes = sorted(
        set(hits) | set(misses) | set(watch),
        key=lambda p: hits[p] + misses[p],
        reverse=True,
    )
    print(f"{'prefix':10} {'support':>8} {'precision%':>11} {'identity_miss%':>15}")
    for p in prefixes:
        support = hits[p] + misses[p]
        if support < support_min and p not in watch:
            continue
        precision = 100 * hits[p] / support if support else 0.0
        id_share = 100 * identity_misses[p] / misses[p] if misses[p] else 0.0
        flag = " <-- watch" if p in watch else ""
        print(f"{p:10} {support:8d} {precision:11.1f} {id_share:15.1f}{flag}")


if __name__ == "__main__":
    lang_arg = sys.argv[1]
    min_len_arg = int(sys.argv[2]) if len(sys.argv) > 2 else MIN_LEN_DEFAULT
    support_min_arg = int(sys.argv[3]) if len(sys.argv) > 3 else SUPPORT_MIN_DEFAULT
    report(lang_arg, min_len_arg, support_min_arg)
