import re
from typing import Optional

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


HYPHENS = {"-", "_"}
HYPHENS_FOR_REGEX = "".join(HYPHENS)
HYPHEN_REGEX = re.compile(rf"([{HYPHENS_FOR_REGEX}])")


class HyphenRemovalStrategy(LemmatizationStrategy):
    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        "Remove hyphens to see if a dictionary form can be found."
        token_parts = HYPHEN_REGEX.split(token)
        if len(token_parts) <= 1 or not token_parts[-1]:
            return None

        # try to find a word form without hyphen
        candidate = "".join([t for t in token_parts if t not in HYPHENS]).lower()
        if token[0].isupper():
            candidate = candidate.capitalize()

        lemma = self._dictionary_lookup.get_lemma(candidate, lang)
        if lemma is not None:
            return lemma

        # decompose
        lemma = self._dictionary_lookup.get_lemma(token_parts[-1], lang)
        if lemma is not None:
            token_parts[-1] = lemma
            return "".join(token_parts)

        return None
