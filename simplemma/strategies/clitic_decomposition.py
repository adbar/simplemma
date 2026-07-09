"""
This file defines the `CliticDecompositionStrategy` class, which strips
clitic chains from a token and reassembles via dictionary lookup on the
stem alone (the clitic is not part of the lemma): enclitics at the end
(fer-ho -> fer, transmitiéndose -> transmitir, don't -> do) and proclitics
at the front (l'arbre -> arbre, qu'il -> il, jusqu'ici -> ici). Same shape
throughout (strip the clitic, verify the remaining stem, drop the
clitic) -- only which end gets stripped differs.
"""

import unicodedata

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

# UD-validated per language (training/data/affix_eval/, MWT verb+clitic
# gold data -- see training/data/affix_eval/README.md "Romance clitics").
# Membership and lists are evidence-gated the same way as AFFIX_LANGS;
# don't add a language or entry without a UD tune/confirm run.
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
    # English auxiliary contractions and possessives. "'s"/"'d" are
    # multi-valued as clitics (be/have/possessive) but the returned STEM
    # lemma is single-valued (UD-validated, en_ewt+en_gum, W=482/L=0).
    # "won't"/"can't"/"shan't" are irregular spellings -- a
    # dictionary-entry gap, not a rule; not handled here.
    "en": ("n't", "'re", "'ve", "'ll", "'m", "'s", "'d"),
}
# English's auxiliary stems (do/is/are/has/had/can/may, and "I" for
# "'m") are far shorter than the Romance verb stems MIN_STEM_LEN was
# calibrated against; a per-language override, same pattern as
# greedy_dictionary_lookup's MIN_LENGTH_OVERRIDES, keeps the Romance
# floor untouched.
MIN_STEM_LEN_OVERRIDES = {"en": 1}
# The capitalized-initial guard assumes capitalization marks a proper
# noun (true for Romance verbs, never capitalized mid-sentence). English
# conflates sentence-initial and proper-noun capitalization ("I'm",
# "Don't") -- the guard doesn't transfer; UD evidence (regression gate)
# shows it's safe to skip for this language.
_CASE_INSENSITIVE_LANGS = {"en"}
# A CLOSED, complete set (not a growing stoplist -- English will never
# add a modal ending in "n"): "n't"-stripping is ambiguous exactly for
# "can" (leaves "ca", which is itself a real dictionary entry --
# California/Canada -- so it verifies *wrong*, not just "fails"), and
# "won't"/"shan't" are irregular spellings where the stripped stem isn't
# the real word at all (will/shall). Excluded outright rather than
# mapped wrong.
_IRREGULAR_CONTRACTIONS = {"can't", "won't", "shan't"}
# Longest-first so a shorter clitic can never shadow a longer one ("os"
# vs "nos"), independent of declaration order (equal-length clitics can't
# match the same ending, so tie order is irrelevant).
CLITIC_LANGS = {
    lang: tuple(sorted(clitics, key=len, reverse=True))
    for lang, clitics in CLITIC_LANGS.items()
}

# UD-validated proclitics (elision before a vowel-initial word), always
# apostrophe-marked in standard orthography -- unlike the enclitic table,
# there's no bare-concatenation form to separately account for. The
# dictionary already has "l'"->"le" etc. as direct keys (see
# training/data/affix_eval/README.md "Apostrophe/proclitic elision"), so
# these entries only need to strip the front and look up the remainder --
# no reattachment, same as the enclitic side. Elided pronouns/articles are
# themselves genuinely ambiguous between readings (fr "s'" soi/si, ca "l'"
# article/pronoun) -- irrelevant here since only the FOLLOWING content
# word's lemma is ever returned, never the proclitic's own.
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
PROCLITIC_LANGS = {
    lang: tuple(sorted(clitics, key=len, reverse=True))
    for lang, clitics in PROCLITIC_LANGS.items()
}

MIN_STEM_LEN = 4  # mirrors affix_decomposition.MINCOMPLEN
# Separately tunable from the enclitic floor above, and much lower: the
# enclitic floor guards against a short STRIPPED STEM spuriously
# verifying in the dictionary (a general risk for any suffix-stripping
# mechanism); an apostrophe followed by just 1-3 letters at the end of a
# token is structurally almost never anything BUT elision in these
# orthographies (unlike a bare short stem, which coincidentally matches
# unrelated real words often), so the equivalent false-fire risk doesn't
# transfer. UD-validated at 1 (monotonically more tokens at every lower
# floor value, zero new regressions at any level, fr/it/ca, both modes,
# fr cross-treebank) -- see training/data/affix_eval/README.md
# "Proclitic floor sweep".
PROCLITIC_MIN_STEM_LEN = 1
MAX_CLITICS = 2  # covers the small multi-clitic tail (e.g. "anar-se'n")
_SEPARATORS = ("-", "'", "")


def _deaccent(word: str) -> str:
    """Strip written accents anywhere in the word (not just the final
    letter) -- enclisis often shifts stress onto a mid-word vowel
    (calificar+le -> calificándole)."""
    decomposed = unicodedata.normalize("NFD", word)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


def _strip_one_clitic(word: str, clitics: tuple[str, ...], min_stem: int) -> str | None:
    for clitic in clitics:
        for sep in _SEPARATORS:
            suffix = sep + clitic
            if word.endswith(suffix) and len(word) - len(suffix) >= min_stem:
                return word[: -len(suffix)]
    return None


def _strip_proclitic(
    word: str, proclitics: tuple[str, ...], min_stem: int
) -> str | None:
    # Curly apostrophes (smart quotes) mark the same elision; NFC does
    # not unify the two variants.
    normalized = word.replace("’", "'")
    for proclitic in proclitics:
        if normalized.startswith(proclitic) and len(word) - len(proclitic) >= min_stem:
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
        """
        Initialize the Clitic Decomposition Strategy.

        Args:
            dictionary_lookup (DictionaryLookupStrategy): The dictionary lookup strategy to use.
                Defaults to `DictionaryLookupStrategy()`.
        """
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get the lemma of a token by stripping a clitic chain, front or back.

        Args:
            token (str): The input token.
            lang (str): The language code.

        Returns:
            str | None: The lemma of the token if found, or None otherwise.
        """
        return self._enclitic_lemma(token, lang) or self._proclitic_lemma(token, lang)

    def _stem_lookup(self, stem: str, lang: str) -> str | None:
        return self._dictionary_lookup.get_lemma(
            stem, lang
        ) or self._dictionary_lookup.get_lemma(_deaccent(stem), lang)

    def _enclitic_lemma(self, token: str, lang: str) -> str | None:
        clitics = CLITIC_LANGS.get(lang)
        # Capitalized-initial tokens are almost always proper nouns in
        # these languages (verbs aren't capitalized mid-sentence); UD
        # evidence shows this is the dominant false-fire source (e.g.
        # Portuguese "Paulo" -> spurious "paul"). Doesn't transfer to
        # English -- see _CASE_INSENSITIVE_LANGS above.
        if clitics is None:
            return None
        if token[:1].isupper() and lang not in _CASE_INSENSITIVE_LANGS:
            return None
        # Curly apostrophes (smart quotes, the default in most editors)
        # must match the straight-apostrophe clitic strings; NFC does
        # not unify the two variants.
        token = token.replace("’", "'")
        if lang == "en" and token.lower() in _IRREGULAR_CONTRACTIONS:
            return None

        min_stem = MIN_STEM_LEN_OVERRIDES.get(lang, MIN_STEM_LEN)
        stem = token
        for _ in range(MAX_CLITICS):
            stripped = _strip_one_clitic(stem, clitics, min_stem)
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
        return self._stem_lookup(stem, lang)
