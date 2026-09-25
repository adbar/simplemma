"""
This file defines the `CliticDecompositionStrategy` class, which strips an
enclitic from a token and looks the remaining stem up in the dictionary (the
clitic is not part of the lemma): portar-lo -> portar, transmitiéndose ->
transmitir, don't -> do. Proclitics (l'arbre -> arbre) are handled by
`PrefixDecompositionStrategy` as drop-prefix languages.
"""

from ..utils import CANON_LANGS, canonicalize_token, strip_diacritics
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


BARE_CHAIN_LANGS = frozenset({"es", "gl"})


class CliticDecompositionStrategy(LemmatizationStrategy):
    """
    Lemmatization strategy that strips one enclitic -- a Romance verb enclitic,
    an English auxiliary contraction, or an Arabic pronoun suffix -- and looks
    up the remaining stem in the dictionary.
    """

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        rules = CLITIC_LANGS.get(lang)
        if rules is None:
            return None
        # fold before matching, like the other dict-matching strategies
        stem = rules.apply(canonicalize_token(token, lang))
        if stem is None:
            return None
        lemma = self._stem_lookup(stem, lang)
        # second strip: hyphen chains (portar-se-la), bare only in es/gl
        # (transmitiéndoselo, UD MWT), not it (diecimila -> dieci)
        if lemma is None and (
            lang in BARE_CHAIN_LANGS
            or stem.endswith(("-me", "-te", "-se", "-nos", "-vos"))
        ):
            stem = rules.apply(stem)
            if stem is not None:
                lemma = self._stem_lookup(stem, lang)
        return lemma

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
