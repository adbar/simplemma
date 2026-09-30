"""Generate prefix-stripping candidates from the shipped dictionaries.

Candidates are hypotheses, not evidence, and must pass the UD gate. A high
identity-miss share flags lexicalized prefixes.

Usage: uv run python training/prefixbuilder.py <lang> [min_len] [support_min]
"""

import sys
from collections import Counter

from simplemma.strategies.affix_decomposition import MINCOMPLEN
from simplemma.strategies.dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
)

FACTORY = DEFAULT_DICTIONARY_FACTORY
MIN_LEN_DEFAULT = 6
SUPPORT_MIN_DEFAULT = 30
PREFIX_LENS = range(2, 7)


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
            if len(form) - plen < MINCOMPLEN:
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
) -> None:
    """Print the ranked candidate table for prefixes with enough support."""
    hits, misses, identity_misses = mine(lang, min_len)
    prefixes = sorted(
        set(hits) | set(misses),
        key=lambda p: hits[p] + misses[p],
        reverse=True,
    )
    print(f"{'prefix':10} {'support':>8} {'precision%':>11} {'identity_miss%':>15}")
    for p in prefixes:
        support = hits[p] + misses[p]
        if support < support_min:
            continue
        precision = 100 * hits[p] / support if support else 0.0
        id_share = 100 * identity_misses[p] / misses[p] if misses[p] else 0.0
        print(f"{p:10} {support:8d} {precision:11.1f} {id_share:15.1f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(
            "Usage: uv run python training/prefixbuilder.py <lang> [min_len] [support_min]"
        )
    lang_arg = sys.argv[1]
    min_len_arg = int(sys.argv[2]) if len(sys.argv) > 2 else MIN_LEN_DEFAULT
    support_min_arg = int(sys.argv[3]) if len(sys.argv) > 3 else SUPPORT_MIN_DEFAULT
    report(lang_arg, min_len_arg, support_min_arg)
