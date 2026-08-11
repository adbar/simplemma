"""Affix decomposition lemmatization strategy."""

from .dictionary_lookup import DictionaryLookupStrategy

# Shared with GreedyDictionaryLookupStrategy's gate on purpose -- retuning
# it retunes both strategies.
from .greedy_dictionary_lookup import greedy_min_length
from .lemmatization_strategy import LemmatizationStrategy

# Membership and max_affix_len values are UD-validated, not in-dict guesswork
# (see training/affixbuilder.py + the gitignored gate under
# training/data/affix_eval/). Many in-dict-positive langs were rejected on UD
# (pt/ca/nl/en/la/gl/fr/it/ro/de); es flipped to member on v2.18 data.
AFFIX_LANGS = {
    "bg": 2,
    "cs": 2,
    "da": 2,
    "el": 2,
    "es": 2,
    "et": 3,
    "fi": 5,
    "hu": 5,
    "hy": 2,
    "lt": 5,
    "lv": 2,
    "nb": 2,
    "nn": 2,
    "pl": 2,
    "ru": 2,
    "sk": 2,
    "tr": 5,
    "uk": 2,
}

# Excluded from greedy-mode decomposition: UD-measured harmful
# (ca/en/gl/it/la/nl/pt), a wash (id), or typologically wrong for suffix
# stripping (ms/sw/tl). it joined once clitics claimed its verb+enclitic
# class, leaving affix to over-fire on -ità/-ismo and proper nouns.
GREEDY_EXCLUDE = {
    "ca",
    "en",
    "gl",
    "id",
    "it",
    "la",
    "ms",
    "nl",
    "pt",
    "sw",
    "tl",
}

AFFIXLEN = 2  # max_affix_len for languages without an AFFIX_LANGS entry (greedy mode)
MINCOMPLEN = 4
# Decomposition is ~O(len²); cap long tokens (longest real form is 86 chars).
MAXLEN = 100


class AffixDecompositionStrategy(LemmatizationStrategy):
    """Affix decomposition: split a token into affix + complement and look up
    the complement in the dictionary; falls back to suffix decomposition."""

    __slots__ = ["_greedy", "_dictionary_lookup"]

    def __init__(
        self,
        greedy: bool,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._greedy = greedy
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        excluded = lang in GREEDY_EXCLUDE if self._greedy else lang not in AFFIX_LANGS
        if excluded or len(token) <= greedy_min_length(lang) or len(token) > MAXLEN:
            return None

        # define parameters
        max_affix_len = AFFIX_LANGS.get(lang, AFFIXLEN)
        return self._affix_decomposition(
            token, lang, max_affix_len, MINCOMPLEN
        ) or self._suffix_decomposition(token, lang, MINCOMPLEN)

    def _affix_decomposition(
        self,
        token: str,
        lang: str,
        max_affix_len: int = 0,
        min_complem_len: int = 0,
    ) -> str | None:
        # Left-to-right languages only. A single pass at the largest affix
        # length is equivalent to looping over smaller ones (first match wins).
        for count in range(1, len(token) - min_complem_len + 1):
            part1 = token[:-count]
            lempart1 = self._dictionary_lookup.get_lemma(part1, lang)
            if lempart1 is None:
                continue
            # maybe an affix? discard it
            if count <= max_affix_len:
                return lempart1
            # account for case before looking for second part
            part2 = token[-count:]
            if token[0].isupper():
                part2 = part2.capitalize()
            lempart2 = self._dictionary_lookup.get_lemma(part2, lang)
            if lempart2 is None:
                continue
            # accept the dictionary form if not longer than the affix bound
            if len(lempart2) < len(part2) + max_affix_len:
                return part1 + lempart2.lower()
        return None

    def _suffix_decomposition(
        self,
        token: str,
        lang: str,
        min_complem_len: int = 0,
    ) -> str | None:
        for count in range(len(token) - min_complem_len, min_complem_len - 1, -1):
            suffix = self._dictionary_lookup.get_lemma(
                token[-count:].capitalize(), lang
            )
            if suffix is not None and len(suffix) <= count:
                return token[:-count] + suffix.lower()

        return None
