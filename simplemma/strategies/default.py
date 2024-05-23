"""
This module defines the `DefaultStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using a combination of different strategies such as dictionary lookup, hyphen removal, rule-based lemmatization, prefix decomposition, and affix decomposition.
"""

from typing import Optional

from .affix_decomposition import AffixDecompositionStrategy
from .dictionaries.dictionary_factory import DefaultDictionaryFactory, DictionaryFactory
from .dictionary_lookup import DictionaryLookupStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .lemmatization_strategy import LemmatizationStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .rules import RulesStrategy


class DefaultStrategy(LemmatizationStrategy):
    """
    This class represents a lemmatization strategy that combines different techniques to perform lemmatization.
    It implements the `LemmatizationStrategy` protocol.
    """

    __slots__ = [
        "_dictionary_lookup",
        "_hyphen_search",
        "_rules_search",
        "_prefix_search",
        "_greedy_dictionary_lookup",
        "_affix_search",
    ]

    def __init__(
        self,
        greedy: bool = False,
        dictionary_factory: DictionaryFactory = DefaultDictionaryFactory(),
    ):
        """
        Initialize the Default Strategy.

        Args:
            greedy (bool): Whether to use a greedy approach for dictionary lookup. Defaults to `False`.
            dictionary_factory (DictionaryFactory): A factory for creating dictionaries.
                Defaults to [`DefaultDictionaryFactory()`][simplemma.strategies.dictionaries.dictionary_factory.DefaultDictionaryFactory]..

        """
        self._greedy = greedy
        self._dictionary_lookup = DictionaryLookupStrategy(dictionary_factory)
        self._hyphen_search = HyphenRemovalStrategy(self._dictionary_lookup)
        self._rules_search = RulesStrategy()
        self._prefix_search = PrefixDecompositionStrategy(
            dictionary_lookup=self._dictionary_lookup
        )
        greedy_dictionary_lookup = GreedyDictionaryLookupStrategy(dictionary_factory)
        self._affix_search = AffixDecompositionStrategy(
            greedy, self._dictionary_lookup, greedy_dictionary_lookup
        )

        self._greedy_dictionary_lookup = greedy_dictionary_lookup if greedy else None

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get the lemma for a given token and language using the combination of different lemmatization techniques.

        Args:
            token (str): The token to lemmatize.
            lang (str): The language of the token.

        Returns:
            Optional[str]: The lemma of the token, or None if no lemma is found.

        """
        # filters
        if token.isnumeric():
            return token

        candidate = (
            # supervised searches
            self._dictionary_lookup.get_lemma(token, lang)
            or self._hyphen_search.get_lemma(token, lang)
            or self._rules_search.get_lemma(token, lang)
            or self._prefix_search.get_lemma(token, lang)
            # weakly supervised / greedier searches
            or self._affix_search.get_lemma(token, lang)
        )

        # additional round
        if candidate is not None and self._greedy_dictionary_lookup is not None:
            candidate = self._greedy_dictionary_lookup.get_lemma(candidate, lang)

        return candidate
