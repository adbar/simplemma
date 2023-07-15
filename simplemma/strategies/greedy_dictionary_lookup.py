"""
This module defines the `GreedyDictionaryLookupStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using a greedy dictionary lookup strategy.
"""

from typing import Optional

from .lemmatization_strategy import LemmatizationStrategy
from .dictionaries.dictionary_factory import DictionaryFactory, DefaultDictionaryFactory
from ..utils import levenshtein_dist

SHORTER_GREEDY = {"bg", "et", "fi"}


class GreedyDictionaryLookupStrategy(LemmatizationStrategy):
    """
    This class represents a lemmatization strategy that performs lemmatization using a greedy dictionary lookup strategy.
    """

    __slots__ = ["_dictionary_factory", "_distance", "_steps"]

    def __init__(
        self,
        dictionary_factory: DictionaryFactory = DefaultDictionaryFactory(),
        steps: int = 1,
        distance: int = 5,
    ):
        """
        Initialize the Greedy Dictionary Lookup Strategy.

        Args:
            dictionary_factory (DictionaryFactory): The dictionary factory used to obtain language dictionaries.
                Defaults to [`DefaultDictionaryFactory()`][simplemma.strategies.dictionaries.dictionary_factory.DefaultDictionaryFactory]..
            steps (int): The maximum number of lemmatization steps to perform. Defaults to `1`.
            distance (int): The maximum allowed Levenshtein distance between candidate lemmas. Defaults to `5`.

        """
        self._dictionary_factory = dictionary_factory
        self._steps = steps
        self._distance = distance

    def get_lemma(self, token: str, lang: str) -> str:
        """
        Get Lemma using Greedy Dictionary Lookup Strategy

        This method performs lemmatization by looking up the token in the language-specific dictionary using a greedy strategy.
        It iteratively applies the dictionary lookup and checks the candidate lemmas based on length and Levenshtein distance.
        It returns the resulting lemma after the specified number of steps or when the conditions are not met.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            str: The lemma for the token.

        """
        limit = 6 if lang in SHORTER_GREEDY else 8
        if len(token) <= limit:
            return token

        dictionary = self._dictionary_factory.get_dictionary(lang)
        candidate = token
        for _ in range(self._steps):
            if candidate not in dictionary:
                break

            new_candidate = dictionary[candidate]

            if (
                len(new_candidate) > len(candidate)
                or levenshtein_dist(new_candidate, candidate) > self._distance
            ):
                break

            candidate = new_candidate

        return candidate
