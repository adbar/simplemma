"""Hyphen-removal lemmatization strategy."""

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

HYPHENS = "-_"


class HyphenRemovalStrategy(LemmatizationStrategy):
    """Look up the part after the last hyphen and keep the head (Mail-Clients
    -> Mail-Client); a head made of hyphens only is dropped (-ce -> ce)."""

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        if "-" not in token and "_" not in token:
            return None
        last = max(token.rfind("-"), token.rfind("_"))
        if last == len(token) - 1:
            return None
        lemma = self._dictionary_lookup.get_lemma(token[last + 1 :], lang)
        if lemma is None:
            return None
        head = token[: last + 1]
        return head + lemma if head.strip(HYPHENS) else lemma
