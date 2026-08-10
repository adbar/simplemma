"""Greedy dictionary lookup lemmatization strategy."""

from ..utils import canonicalize_token, levenshtein_dist
from .dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DictionaryFactory,
)
from .lemmatization_strategy import LemmatizationStrategy

# UD-validated per language (see training/data/affix_eval/); shared with
# the affix entry gate in affix_decomposition.py on purpose.
MIN_LENGTH_OVERRIDES = {"bg": 6, "et": 6, "fi": 6, "lt": 7, "lv": 6}


def greedy_min_length(lang: str) -> int:
    """Shortest token worth decomposing; shorter ones are returned/skipped as-is."""
    return MIN_LENGTH_OVERRIDES.get(lang, 8)


class GreedyDictionaryLookupStrategy(LemmatizationStrategy):
    """Iterative dictionary chase: follow the dict's value as a key, up to
    `steps` times, bounded by edit distance."""

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
        # no-op for unregistered langs: matches DictionaryLookupStrategy's
        # canonicalization, so a vocalized/accented token still resolves
        # when this strategy is used standalone or reordered ahead of it.
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
