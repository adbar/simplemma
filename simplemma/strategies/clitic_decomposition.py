"""
This file defines the `CliticDecompositionStrategy` class, which strips a
clitic from a token and looks the remaining stem up in the dictionary (the
clitic is not part of the lemma): enclitics at the end (portar-lo -> portar,
transmitiéndose -> transmitir, don't -> do) and proclitics at the front
(l'arbre -> arbre, qu'il -> il, jusqu'ici -> ici). Same shape throughout
(strip the clitic, verify the remaining stem, drop the clitic) -- only which
end gets stripped differs.
"""

from ..utils import CANON_LANGS, canonicalize_token, longest_first, strip_diacritics
from .defaultrules.generic import SuffixRules
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

MIN_STEM_LEN = 4  # mirrors affix_decomposition.MINCOMPLEN

# Enclitics as suffix tables that strip (empty target); the clitic is spelled
# as it attaches in UD MWT gold: bare, or with its mandatory hyphen/apostrophe
# (pt/ca have no bare gold surfaces, so a bare strip would only mangle OOV
# words ending in a clitic shape: paulo -> paul; gl attaches both ways).
# `caps`: a capitalized token is a proper noun here (dominant false-fire,
# "Paulo" -> "paul"). UD-validated per language, evidence-gated like
# AFFIX_LANGS -- see training/data/affix_eval/README.md "Romance clitics".
CLITIC_LANGS: dict[str, SuffixRules] = {
    "es": SuffixRules(
        {"": "nos les las los me te se le la lo os"}, min_stem=MIN_STEM_LEN, caps=True
    ),
    "pt": SuffixRules(
        {
            "": "-lhes -nos -vos -lhe -las -los -me -te -se -la -lo -na -no -as -os -a -o"
        },
        min_stem=MIN_STEM_LEN,
        caps=True,
    ),
    "ca": SuffixRules(
        {
            "": (
                "-nos 'nos -les 'les -los 'los -me 'me -te 'te -se 'se -le 'le -la"
                " 'la -lo 'lo -hi 'hi -ho 'ho -ne 'ne -el 'el -en 'en -li 'li"
            )
        },
        min_stem=MIN_STEM_LEN,
        caps=True,
    ),
    "it": SuffixRules(
        {"": "gli vi ci si mi ti ne lo la le li"}, min_stem=MIN_STEM_LEN, caps=True
    ),
    "gl": SuffixRules(
        {
            "": "-lles lles -lle lle -nos nos -vos vos -me me -te te -se se -as as -os os -a a -o o"
        },
        min_stem=MIN_STEM_LEN,
        caps=True,
    ),
    # English contractions/possessives; the stem lemma is single-valued even
    # for multi-valued "'s"/"'d". Auxiliary stems (do/is/I...) are short, and
    # English conflates sentence-initial and proper-noun caps ("I'm"), so
    # neither the Romance stem floor nor the caps guard applies. Stripping
    # "n't" off can't/won't/shan't leaves a wrong real word: excluded.
    "en": SuffixRules(
        {"": "n't 're 've 'll 'm 's 'd"},
        min_stem=1,
        excluded=frozenset({"can't", "won't", "shan't"}),
    ),
    # Arabic possessive/object pronoun suffixes (UD-validated, +0.57pp).
    # ك/ي EXCLUDED: they collide with native root-final letters/nisba
    # endings and net WORSE accuracy despite more raw fixes.
    "ar": SuffixRules({"": "هن هم ها ه كم نا"}, min_stem=MIN_STEM_LEN, caps=True),
}

# UD-validated proclitics (vowel-elision, always apostrophe-marked). Strip the
# front and look up the remainder; the proclitic's own lemma is never returned.
# Longest first, so a short proclitic can't shadow a longer one.
# See training/data/affix_eval/README.md "Apostrophe/proclitic elision".
PROCLITIC_LANGS: dict[str, tuple[str, ...]] = {
    "fr": longest_first(
        "jusqu' lorsqu' puisqu' quoiqu' presqu' qu' l' d' c' n' s' m' j' t'".split()
    ),
    "it": longest_first(
        "quest' quell' dell' nell' sull' coll' dall' un' l' d' c' s'".split()
    ),
    "ca": longest_first("l' d' s' m' n' t'".split()),
}
# Much lower than the enclitic floor: an apostrophe + 1-3 trailing letters is
# almost always elision, so the short-stem false-fire risk doesn't apply.
# UD-validated at 1 -- see README.md "Proclitic floor sweep".
PROCLITIC_MIN_STEM_LEN = 1


def _strip_proclitic(
    word: str, proclitics: tuple[str, ...], min_stem: int
) -> str | None:
    # Lowercase so a sentence-initial L'homme still matches.
    lowered = word.lower()
    # Every proclitic ends in an apostrophe, so a token without one can't match.
    if "'" not in lowered:
        return None
    for proclitic in proclitics:
        if lowered.startswith(proclitic) and len(word) - len(proclitic) >= min_stem:
            return word[len(proclitic) :]
    return None


class CliticDecompositionStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy that strips one clitic -- a Romance verb enclitic,
    an English auxiliary contraction, or a Romance proclitic elision -- and
    looks up the remaining stem in the dictionary.
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
        # Enclisis can add a stress accent (calificar+le -> calificándole): retry
        # folded. Not for CANON_LANGS: their lookup fold is the right one, and a
        # blind mark strip would decompose ar hamza letters onto unrelated words.
        if lemma is not None or lang in CANON_LANGS:
            return lemma
        folded = strip_diacritics(stem)
        if folded == stem:
            return None
        return self._dictionary_lookup.get_lemma(folded, lang)

    def _enclitic_lemma(self, token: str, lang: str) -> str | None:
        rules = CLITIC_LANGS.get(lang)
        if rules is None:
            return None
        stem = rules.apply(token)
        if stem is None:
            return None
        lemma = self._stem_lookup(stem, lang)
        # hyphen chains (portar-se-la) get one more strip; bare ones don't (UD: diecimila -> dieci)
        if lemma is None and stem.endswith(("-me", "-te", "-se", "-nos", "-vos")):
            stem = rules.apply(stem)
            if stem is not None:
                lemma = self._stem_lookup(stem, lang)
        return lemma

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
