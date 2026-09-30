"""Morpheme decomposition for languages that stack affixes on one root (tl, id).

Candidates combine prefix, infix, reduplication and suffix strips.
One is accepted only if it is a dictionary entry.
"""

from collections.abc import Iterator
from typing import NamedTuple

from ..utils import longest_first
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

_TL_PREFIXES = (
    "magkaka nagkaka makapag nakapag magpaka nagpaka makipag nakipag nagpapa "
    "magpapa magka nagka nakaka makaka ipinag ipinang magsi nagsi ipang ipag ikina "
    "ipina pinag maka naka magpa nagpa maki naki mang nang ika ipa mag nag ma na "
    "pa ka um in i"
)
# "ng" and "g" are the fused linker (magandang, ulang)
_TL_SUFFIXES = "han hin an in ng g"

MIN_STEM_LEN = 3
_VOWELS = frozenset("aeiou")


class _Morphemes(NamedTuple):
    prefixes: tuple[str, ...]
    suffixes: tuple[str, ...]
    infixes: tuple[str, ...]


def _morphemes(prefixes: str, suffixes: str, infixes: str = "") -> _Morphemes:
    """Affix inventory from space-separated lists, sorted longest-first."""
    return _Morphemes(
        longest_first(prefixes.split()),
        longest_first(suffixes.split()),
        longest_first(infixes.split()),
    )


MORPHEME_LANGS: dict[str, _Morphemes] = {
    "tl": _morphemes(_TL_PREFIXES, _TL_SUFFIXES, infixes="um in"),
    "id": _morphemes(
        # bare me/ke/se/pe left out on purpose: they overfire
        "memper diper meng meny mem men ber ter di",
        "kan i an",
    ),
}


# deepest strip first: a shallow one can hit an unrelated entry (maiiwasan -> iiwas)


def _strip_prefix_candidates(token: str, prefixes: tuple[str, ...]) -> Iterator[str]:
    for prefix in prefixes:
        if token.startswith(prefix):
            yield token[len(prefix) :]
    yield token


def _strip_infix_candidates(stem: str, infixes: tuple[str, ...]) -> Iterator[str]:
    if stem[:1] and stem[0] not in _VOWELS:
        for infix in infixes:
            if stem[1 : 1 + len(infix)] == infix:
                yield stem[0] + stem[1 + len(infix) :]
    yield stem


def _fold_reduplication_candidates(stem: str) -> Iterator[str]:
    for unit_len in (2, 1):
        if stem[:unit_len] and stem[:unit_len] == stem[unit_len : 2 * unit_len]:
            yield stem[unit_len:]
    yield stem


def _strip_suffix_candidates(stem: str, suffixes: tuple[str, ...]) -> Iterator[str]:
    for suffix in suffixes:
        if stem.endswith(suffix):
            yield stem[: -len(suffix)]
    yield stem


def _candidates(working: str, morphemes: "_Morphemes") -> Iterator[str]:
    """All decomposition residues of `working`, deepest-first."""
    for prefix_stem in _strip_prefix_candidates(working, morphemes.prefixes):
        for infix_stem in _strip_infix_candidates(prefix_stem, morphemes.infixes):
            for redup_stem in _fold_reduplication_candidates(infix_stem):
                yield from _strip_suffix_candidates(redup_stem, morphemes.suffixes)


class MorphemeDecompositionStrategy(LemmatizationStrategy):
    """Strip stacked affixes, keep a residue found in the dictionary."""

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        morphemes = MORPHEME_LANGS.get(lang)
        if morphemes is None:
            return None
        # lowercase a sentence-initial capital so the affixes match
        working = token[:1].lower() + token[1:] if token[:1].isupper() else token

        seen = {token, working}
        for candidate in _candidates(working, morphemes):
            if len(candidate) < MIN_STEM_LEN or candidate in seen:
                continue
            seen.add(candidate)
            lemma = self._dictionary_lookup.get_lemma(candidate, lang)
            if lemma is not None:
                return lemma
        return None
