"""
This file defines the `CliticDecompositionStrategy` class, which strips
clitic chains from a token and reassembles via dictionary lookup on the
stem alone (the clitic is not part of the lemma): enclitics at the end
(portar-lo -> portar, transmitiéndose -> transmitir, don't -> do) and proclitics
at the front (l'arbre -> arbre, qu'il -> il, jusqu'ici -> ici). Same shape
throughout (strip the clitic, verify the remaining stem, drop the
clitic) -- only which end gets stripped differs.
"""

from ..utils import (
    CANON_LANGS,
    canonicalize_token,
    normalize_apostrophes,
    strip_diacritics,
)
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

# UD-validated per language (MWT verb+clitic gold); evidence-gated like
# AFFIX_LANGS -- see training/data/affix_eval/README.md "Romance clitics".
CLITIC_LANGS: dict[str, tuple[str, ...]] = {
    "es": ("nos", "les", "las", "los", "me", "te", "se", "le", "la", "lo", "os"),
    "pt": (
        "lhes",
        "nos",
        "vos",
        "lhe",
        "las",
        "los",
        "me",
        "te",
        "se",
        "la",
        "lo",
        "na",
        "no",
        "as",
        "os",
        "a",
        "o",
    ),
    "ca": (
        "nos",
        "les",
        "los",
        "me",
        "te",
        "se",
        "le",
        "la",
        "lo",
        "hi",
        "ho",
        "ne",
        "el",
        "en",
        "li",
    ),
    "it": ("gli", "vi", "ci", "si", "mi", "ti", "ne", "lo", "la", "le", "li"),
    "gl": ("lles", "lle", "nos", "vos", "me", "te", "se", "as", "os", "a", "o"),
    # English contractions/possessives; the stem lemma is single-valued even
    # for multi-valued "'s"/"'d". Irregulars won't/can't/shan't handled below.
    "en": ("n't", "'re", "'ve", "'ll", "'m", "'s", "'d"),
    # Arabic possessive/object pronoun suffixes (UD-validated, +0.57pp).
    # ك/ي EXCLUDED: they collide with native root-final letters/nisba
    # endings and net WORSE accuracy despite more raw fixes.
    "ar": ("هن", "هم", "ها", "ه", "كم", "نا"),
}
# English auxiliary stems (do/is/I...) are shorter than Romance verb stems.
MIN_STEM_LEN_OVERRIDES = {"en": 1}
# English conflates sentence-initial and proper-noun caps ("I'm"), so the
# proper-noun guard doesn't transfer (UD-safe to skip).
_CASE_INSENSITIVE_LANGS = {"en"}
# Closed set: stripping "n't" leaves a wrong real word ("can"->"ca";
# won't/shan't are will/shall). Excluded, not mapped.
_IRREGULAR_CONTRACTIONS: dict[str, frozenset[str]] = {
    "en": frozenset({"can't", "won't", "shan't"}),
}
# How a clitic attaches (UD MWT gold): bare concatenation by default; only
# exceptions are listed. pt/ca omit the bare form entirely: they mandate a
# hyphen (no bare gold surfaces), so a bare strip only mangles OOV words
# ending in a clitic shape (paulo -> paul).
_CLITIC_SEPARATORS: dict[str, tuple[str, ...]] = {
    "pt": ("-",),
    "ca": ("-", "'"),
    "gl": ("-", ""),
}
# Precompute "separator + clitic" suffixes once, longest clitic first so a
# short one can't shadow a longer one; clitic-major order = first-match order.
_CLITIC_SUFFIXES = {
    lang: tuple(
        sep + clitic
        for clitic in sorted(clitics, key=len, reverse=True)
        for sep in _CLITIC_SEPARATORS.get(lang, ("",))
    )
    for lang, clitics in CLITIC_LANGS.items()
}

# UD-validated proclitics (vowel-elision, always apostrophe-marked). Strip the
# front and look up the remainder; the proclitic's own lemma is never returned.
# See training/data/affix_eval/README.md "Apostrophe/proclitic elision".
PROCLITIC_LANGS: dict[str, tuple[str, ...]] = {
    "fr": (
        "jusqu'",
        "lorsqu'",
        "puisqu'",
        "quoiqu'",
        "presqu'",
        "qu'",
        "l'",
        "d'",
        "c'",
        "n'",
        "s'",
        "m'",
        "j'",
        "t'",
    ),
    "it": (
        "quest'",
        "quell'",
        "dell'",
        "nell'",
        "sull'",
        "coll'",
        "dall'",
        "un'",
        "l'",
        "d'",
        "c'",
        "s'",
    ),
    "ca": ("l'", "d'", "s'", "m'", "n'", "t'"),
}
# Longest first, so a short proclitic can't shadow a longer one (as above).
PROCLITIC_LANGS = {
    lang: tuple(sorted(proclitics, key=len, reverse=True))
    for lang, proclitics in PROCLITIC_LANGS.items()
}
MIN_STEM_LEN = 4  # mirrors affix_decomposition.MINCOMPLEN
# Much lower than the enclitic floor: an apostrophe + 1-3 trailing letters is
# almost always elision, so the short-stem false-fire risk doesn't apply.
# UD-validated at 1 -- see README.md "Proclitic floor sweep".
PROCLITIC_MIN_STEM_LEN = 1
MAX_CLITICS = 2  # covers the small multi-clitic tail (e.g. "portar-se-la")


def _strip_one_clitic(
    word: str, suffixes: tuple[str, ...], min_stem: int
) -> str | None:
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= min_stem:
            return word[: -len(suffix)]
    return None


def _strip_proclitic(
    word: str, proclitics: tuple[str, ...], min_stem: int
) -> str | None:
    # Fold smart quotes; lowercase so a sentence-initial L'homme still matches.
    lowered = normalize_apostrophes(word).lower()
    # Every proclitic ends in an apostrophe, so a token without one can't match.
    if "'" not in lowered:
        return None
    for proclitic in proclitics:
        if lowered.startswith(proclitic) and len(word) - len(proclitic) >= min_stem:
            return word[len(proclitic) :]
    return None


class CliticDecompositionStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy that strips a clitic chain -- Romance verb
    enclitics, English auxiliary contractions, or Romance proclitic
    elision -- and looks up the remaining stem in the dictionary.
    """

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        # fold before matching, like the other dict-matching strategies
        token = canonicalize_token(token, lang)
        return self._enclitic_lemma(token, lang) or self._proclitic_lemma(token, lang)

    def _stem_lookup(self, stem: str, lang: str) -> str | None:
        lemma = self._dictionary_lookup.get_lemma(stem, lang)
        if lemma is not None:
            return lemma
        # For a CANON_LANGS language the lookup already applied the right
        # fold; strip_diacritics (a blind NFD mark strip, built for Romance
        # stress accents) would also decompose ar hamza letters
        # (مؤمن -> مومن, an unrelated real word) and land on wrong entries.
        if lang in CANON_LANGS:
            return None
        # Enclisis can add a stress accent (calificar+le -> calificándole);
        # retry folded, but only if folding changes the stem.
        folded = strip_diacritics(stem)
        if folded == stem:
            return None
        return self._dictionary_lookup.get_lemma(folded, lang)

    def _enclitic_lemma(self, token: str, lang: str) -> str | None:
        suffixes = _CLITIC_SUFFIXES.get(lang)
        if suffixes is None:
            return None
        # Capitalized-initial = proper noun here (dominant false-fire, e.g.
        # "Paulo"->"paul"); doesn't apply to English (_CASE_INSENSITIVE_LANGS).
        if token[:1].isupper() and lang not in _CASE_INSENSITIVE_LANGS:
            return None
        token = normalize_apostrophes(token)  # match straight-apostrophe clitics
        if token.lower() in _IRREGULAR_CONTRACTIONS.get(lang, frozenset()):
            return None

        min_stem = MIN_STEM_LEN_OVERRIDES.get(lang, MIN_STEM_LEN)
        stem = token
        for _ in range(MAX_CLITICS):
            stripped = _strip_one_clitic(stem, suffixes, min_stem)
            if stripped is None:
                return None
            stem = stripped
            lemma = self._stem_lookup(stem, lang)
            if lemma is not None:
                return lemma
        return None

    def _proclitic_lemma(self, token: str, lang: str) -> str | None:
        proclitics = PROCLITIC_LANGS.get(lang)
        if proclitics is None:
            return None
        stem = _strip_proclitic(token, proclitics, PROCLITIC_MIN_STEM_LEN)
        if stem is None:
            return None
        # Capitalized stem after a capitalized proclitic = proper noun
        # (D'Annunzio, don't strip); lowercase stem = sentence-initial (L'homme).
        if token[:1].isupper() and stem[:1].isupper():
            return None
        return self._stem_lookup(stem, lang)
