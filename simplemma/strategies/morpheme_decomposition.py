"""
This module defines the `MorphemeDecompositionStrategy` class, for languages
whose inflectional morphology is COMPOSITIONAL -- several affixes (prefix
chain, infix, reduplication, suffix) stack on one root, and all of them
must be discarded together to reach the lemma. Unlike
`PrefixDecompositionStrategy` (one bounded strip from a fixed list),
this is a multi-stage search: it generates a bounded set of candidate
residues (prefix strip x infix strip x reduplication fold x suffix strip)
and accepts ONE only if it is an independently attested dictionary
entry -- a false accept needs both a morpheme-shaped affix run AND a
coincidental dictionary collision on the residue.

Tagalog is the first target: actor/object/locative/causative focus
prefixes (`mag-`/`nag-`, `ma-`/`na-`, `maka-`/`naka-`, ...), the
`-um-`/`-in-` infixes, aspect reduplication (`iwas` -> `maiiwasan`), and
object-focus suffixes (`-in`/`-an`/`-han`/`-hin`) all attach to ONE root
that is the lemma itself. Indonesian (prefix + suffix, no infix) is the
second. Swahili's prefix system is similarly compositional but needs
iterative multi-morpheme stripping (not attempted here; a flat prefix
list measured net-negative on sw).
"""

from collections.abc import Iterator
from dataclasses import dataclass

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

# Tagalog verbal-focus prefixes. Not exhaustive -- covers the high-frequency
# actor/object/ability/causative/instrumental/reciprocal/distributive/
# intensive paradigms; gated on real UD text (tune=nc-dev,
# confirm=nc-test+trg+ugnayan), not hand-picked.
_TL_PREFIXES = (
    "magkaka",
    "nagkaka",
    "makapag",
    "nakapag",
    "magpaka",
    "nagpaka",
    "makipag",
    "nakipag",
    "nagpapa",
    "magpapa",
    "magka",
    "nagka",
    "nakaka",
    "makaka",
    "ipinag",
    "ipinang",
    "magsi",
    "nagsi",
    "ipang",
    "ipag",
    "ikina",
    "ipina",
    "pinag",
    "maka",
    "naka",
    "magpa",
    "nagpa",
    "maki",
    "naki",
    "mang",
    "nang",
    "ika",
    "ipa",
    "mag",
    "nag",
    "ma",
    "na",
    "pa",
    "ka",
    "um",
    "in",
    "i",
)
# Object/locative-focus suffixes, plus the linker (ligature) na fused onto
# its host: vowel-final host + "ng" (maganda -> magandang), n-final host +
# "g" (ulan -> ulang). Real text never splits the linker off, so the fused
# form must be decomposed at runtime; dict verification gates the residue
# (measured +1.1 to +2.9pp real-word on all 4 tl treebanks, at the cost of
# a -0.1pp per-sub-token dip on newscrawl from unconstrained "g" strips).
_TL_SUFFIXES = ("han", "hin", "an", "in", "ng", "g")

MIN_STEM_LEN = 3
_VOWELS = frozenset("aeiou")


@dataclass(frozen=True)
class _Morphemes:
    """Per-language affix inventory. Order in the literals doesn't matter:
    __post_init__ sorts longest-first, which the candidate search relies on
    (a longer real match must be tried before a shorter prefix of it)."""

    prefixes: tuple[str, ...]
    suffixes: tuple[str, ...]
    infixes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for f in ("prefixes", "suffixes", "infixes"):
            object.__setattr__(
                self, f, tuple(sorted(getattr(self, f), key=len, reverse=True))
            )


MORPHEME_LANGS: dict[str, _Morphemes] = {
    # A vowel-alternation stage (gusto+han -> gustuhan, fold u->o back) was
    # tried and removed: <=0.3pp on one treebank, no verdict changes -- not
    # worth a config dimension.
    "tl": _Morphemes(
        prefixes=_TL_PREFIXES,
        suffixes=_TL_SUFFIXES,
        infixes=("um", "in"),
    ),
    "id": _Morphemes(
        # Indonesian verbal affixes; conservative on purpose -- short/ambiguous
        # prefixes (me/ke/se/pe alone, without their consonant-initial variants)
        # measured net-negative (overfire on unrelated words) in an earlier A/B.
        prefixes=("memper", "diper", "meng", "meny", "mem", "men", "ber", "ter", "di"),
        suffixes=("kan", "i", "an"),
    ),
}


# Every generator below yields its MODIFIED candidate(s) before the untouched
# stem: trying the most-decomposed residue first avoids a shallow strip
# landing on an unrelated-but-real dict entry before the true root is tried
# (measured: "maiiwasan" hit "iiwas"->"umiwas" before the correct "iwas").
# None of these enforce MIN_STEM_LEN themselves -- every later stage only
# shortens the string further, so a single floor check on the final
# candidate (in get_lemma) is equivalent to checking it at each stage.


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
    """
    Lemmatization strategy that strips a bounded set of compositional
    affixes (prefix chain, infix, reduplication, suffix) for languages
    configured in `MORPHEME_LANGS`, accepting a decomposition only if the
    residue is a real dictionary entry.
    """

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        morphemes = MORPHEME_LANGS.get(lang)
        if morphemes is None:
            return None
        # Lowercase a sentence-initial capital so lowercase affixes match
        # (interior/all-caps left as-is); verb lemmas are lowercase, so look
        # the residue up as-is rather than reconstructing casing.
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
