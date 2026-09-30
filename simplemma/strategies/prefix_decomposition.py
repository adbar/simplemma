"""Prefix decomposition lemmatization strategy."""

import re

from ..utils import canonicalize_token, longest_first
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


def _prefix_regex(prefixes: str, suffix: str = "") -> re.Pattern[str]:
    return re.compile(r"^(" + "|".join(longest_first(prefixes.split())) + r")" + suffix)


DEFAULT_KNOWN_PREFIXES: dict[str, re.Pattern[str]] = {
    # (?=..) keeps a short token from stripping to a one-letter abbreviation key
    "ar": _prefix_regex("و ب ل ال لل وال بال فال كال", r"(?=..)"),
    "ca": _prefix_regex("l' d' s' m' n' t'"),
    "fr": _prefix_regex(
        "jusqu' lorsqu' puisqu' quoiqu' presqu' qu' l' d' c' n' s' m' j' t'"
    ),
    "it": _prefix_regex("quest' quell' dell' nell' sull' coll' dall' un' l' d' c' s'"),
    # מ is left out on purpose: too many false splits
    "he": _prefix_regex("ו ה ב כ ל ש", r"(?=..)"),
    "uk": _prefix_regex("по за ви на при про роз пере від до під об без"),
}

# prefix is a dropped particle (l'arbre -> arbre), matched case-insensitively
DROP_PREFIX_LANGS = frozenset({"ar", "he", "ca", "fr", "it"})


class PrefixDecompositionStrategy(LemmatizationStrategy):
    """Strip a known prefix and look up the remainder."""

    __slots__ = ["_known_prefixes", "_dictionary_lookup"]

    def __init__(
        self,
        known_prefixes: dict[str, re.Pattern[str]] = DEFAULT_KNOWN_PREFIXES,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._known_prefixes = known_prefixes
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        if lang not in self._known_prefixes:
            return None

        # fold first: ar tashkeel sits between the letters of a fused prefix
        token = canonicalize_token(token, lang)
        drop = lang in DROP_PREFIX_LANGS
        prefix_match = self._known_prefixes[lang].match(
            token.lower() if drop else token
        )
        if not prefix_match or prefix_match.end() == len(token):
            return None

        stem = token[prefix_match.end() :]
        # capitalized particle and stem is a proper noun (D'Annunzio)
        if drop and token[:1].isupper() and stem[:1].isupper():
            return None

        subword = self._dictionary_lookup.get_lemma(stem, lang)
        if not subword:
            return None

        if drop:
            return subword

        return token[: prefix_match.end()] + subword.lower()
