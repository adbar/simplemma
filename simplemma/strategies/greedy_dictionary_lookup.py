"""Greedy dictionary lookup lemmatization strategy."""

from ..utils import canonicalize_token, levenshtein_dist
from .dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DictionaryFactory,
)
from .lemmatization_strategy import LemmatizationStrategy

# shared with affix_decomposition on purpose
MIN_LENGTH_OVERRIDES = {"bg": 6, "et": 6, "fi": 6, "is": 6, "lt": 7, "lv": 6}


def greedy_min_length(lang: str) -> int:
    """Shortest token worth decomposing."""
    return MIN_LENGTH_OVERRIDES.get(lang, 8)


class GreedyDictionaryLookupStrategy(LemmatizationStrategy):
    """Follow dictionary values as keys up to `steps` times, within an edit distance."""

    __slots__ = ["_dictionary_factory", "_distance", "_steps"]

    def __init__(
        self,
        dictionary_factory: DictionaryFactory = DEFAULT_DICTIONARY_FACTORY,
        steps: int = 1,
        distance: int = 5,
    ):
        self._dictionary_factory = dictionary_factory
        self._steps = steps
        self._distance = distance

    def get_lemma(self, token: str, lang: str) -> str:
        # canonicalize here too, for standalone use
        token = canonicalize_token(token, lang)
        if len(token) <= greedy_min_length(lang):
            return token

        dictionary = self._dictionary_factory.get_dictionary(lang)

        for _ in range(self._steps):
            candidate = dictionary.get(token)

            if (
                not candidate
                or len(candidate) > len(token)
                or levenshtein_dist(candidate, token) > self._distance
            ):
                break

            token = candidate

        return token
