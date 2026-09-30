"""Affix decomposition lemmatization strategy."""

from .dictionary_lookup import DictionaryLookupStrategy

# shared with GreedyDictionaryLookupStrategy on purpose
from .greedy_dictionary_lookup import greedy_min_length
from .lemmatization_strategy import LemmatizationStrategy

AFFIX_LANGS = {
    "bg": 2,
    "cs": 2,
    "da": 2,
    "el": 2,
    "et": 2,
    "fi": 4,
    "hbs": 2,
    "hu": 4,
    "hy": 2,
    "is": 2,
    "lt": 5,
    "lv": 2,
    "nb": 2,
    "nn": 2,
    "pl": 2,
    "ro": 2,
    "ru": 3,
    "sk": 2,
    "sl": 2,
    "sv": 2,
    "tr": 5,
    "uk": 2,
}

GREEDY_EXCLUDE = frozenset("ca en gl id it la ms nl pt sw tl".split())

AFFIXLEN = 2  # max_affix_len for languages without an AFFIX_LANGS entry (greedy mode)
MINCOMPLEN = 4
# decomposition is quadratic in token length
MAXLEN = 100


class AffixDecompositionStrategy(LemmatizationStrategy):
    """Split off an affix and look up the rest, else try suffix decomposition."""

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

        return self._affix_decomposition(
            token, lang, AFFIX_LANGS.get(lang, AFFIXLEN)
        ) or self._suffix_decomposition(token, lang)

    def _affix_decomposition(
        self, token: str, lang: str, max_affix_len: int
    ) -> str | None:
        """Strip up to `max_affix_len` final chars; greedy also splits compounds."""
        last = len(token) - MINCOMPLEN
        for count in range(1, (last if self._greedy else min(max_affix_len, last)) + 1):
            lemma = self._dictionary_lookup.get_lemma(token[:-count], lang)
            if lemma is None:
                continue
            if count <= max_affix_len:
                return lemma
            part2 = token[-count:]
            if token[0].isupper():
                part2 = part2.capitalize()
            lempart2 = self._dictionary_lookup.get_lemma(part2, lang)
            if lempart2 is not None and len(lempart2) < len(part2) + max_affix_len:
                return token[:-count] + lempart2.lower()
        return None

    def _suffix_decomposition(self, token: str, lang: str) -> str | None:
        for count in range(len(token) - MINCOMPLEN, MINCOMPLEN - 1, -1):
            suffix = self._dictionary_lookup.get_lemma(
                token[-count:].capitalize(), lang
            )
            if suffix is not None and len(suffix) <= count:
                return token[:-count] + suffix.lower()

        return None
