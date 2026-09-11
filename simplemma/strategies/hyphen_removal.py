"""Hyphen-removal lemmatization strategy."""

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

HYPHENS = ("-", "_")


class HyphenRemovalStrategy(LemmatizationStrategy):
    """Remove hyphens and look up the joined form; fall back to decomposing
    at the last hyphen and looking up the tail."""

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        last = max(token.rfind(h) for h in HYPHENS)
        if last < 0 or last == len(token) - 1:
            return None

        # try to find a word form without hyphen
        candidate = token.lower()
        for hyphen in HYPHENS:
            candidate = candidate.replace(hyphen, "")
        if token[0].isupper():
            candidate = candidate.capitalize()
        lemma = self._dictionary_lookup.get_lemma(candidate, lang)
        if lemma is not None:
            return lemma

        # decompose at the last hyphen
        last_part_lemma = self._dictionary_lookup.get_lemma(token[last + 1 :], lang)
        if last_part_lemma is not None:
            return token[: last + 1] + last_part_lemma
        return None
