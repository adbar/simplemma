"""Hyphen-removal lemmatization strategy."""

import re

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

HYPHENS = {"-", "_"}
HYPHEN_REGEX = re.compile(rf"([{''.join(HYPHENS)}])")


class HyphenRemovalStrategy(LemmatizationStrategy):
    """Remove hyphens and look up the joined form; fall back to decomposing
    at the last hyphen and looking up the tail."""

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        if not any(hyphen in token for hyphen in HYPHENS):
            return None
        token_parts = HYPHEN_REGEX.split(token)
        if not token_parts[-1]:
            return None

        # try to find a word form without hyphen
        candidate = "".join([t for t in token_parts if t not in HYPHENS]).lower()
        if token[0].isupper():
            candidate = candidate.capitalize()

        lemma = self._dictionary_lookup.get_lemma(candidate, lang)
        if lemma is not None:
            return lemma

        # decompose
        last_part_lemma = self._dictionary_lookup.get_lemma(token_parts[-1], lang)
        if last_part_lemma is not None:
            return "".join(token_parts[:-1] + [last_part_lemma])

        return None
