"""
Default Strategy
----------------

This module defines the `DefaultStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using a combination of different strategies such as dictionary lookup, hyphen removal, rule-based lemmatization, prefix decomposition, and affix decomposition.

Module Dependencies:
- typing.Optional: For representing an optional return value.

Class:
- `DefaultStrategy`: A lemmatization strategy that combines different lemmatization techniques.

"""

from typing import Optional

from .dictionaries.dictionary_factory import DictionaryFactory, DefaultDictionaryFactory
from .lemmatization_strategy import LemmatizationStrategy
from .dictionary_lookup import DictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .rules import RulesStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .affix_decomposition import AffixDecompositionStrategy


class DefaultStrategy(LemmatizationStrategy):
    """
    Default Strategy

    This class represents a lemmatization strategy that combines different techniques to perform lemmatization.
    It implements the `LemmatizationStrategy` protocol.

    Attributes:
    - `_dictionary_lookup` (DictionaryLookupStrategy): A strategy for dictionary lookup.
    - `_hyphen_search` (HyphenRemovalStrategy): A strategy for lemmatization by removing hyphens.
    - `_rules_search` (RulesStrategy): A strategy for rule-based lemmatization.
    - `_prefix_search` (PrefixDecompositionStrategy): A strategy for lemmatization by prefix decomposition.
    - `_greedy_dictionary_lookup` (Optional[GreedyDictionaryLookupStrategy]): A strategy for dictionary lookup with a greedy approach.
    - `_affix_search` (AffixDecompositionStrategy): A strategy for lemmatization by affix decomposition.

    Methods:
    - `get_lemma`: Get the lemma for a given token and language using the combination of different techniques.

    """

    __slots__ = [
        "_dictionary_lookup",
        "_hyphen_search",
        "_rules_search",
        "_prefix_search",
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
        - `greedy` (bool): Whether to use a greedy approach for dictionary lookup. Defaults to `False`.
        - `dictionary_factory` (DictionaryFactory): A factory for creating dictionaries.
            Defaults to `DefaultDictionaryFactory()`.

        """
        self._dictionary_lookup = (
            GreedyDictionaryLookupStrategy(dictionary_factory)
            if greedy
            else DictionaryLookupStrategy(dictionary_factory)
        )
        self._hyphen_search = HyphenRemovalStrategy(self._dictionary_lookup)
        self._rules_search = RulesStrategy()
        self._prefix_search = PrefixDecompositionStrategy(
            dictionary_lookup=self._dictionary_lookup
        )
        self._affix_search = AffixDecompositionStrategy(self._dictionary_lookup)

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get the lemma for a given token and language using the combination of different lemmatization techniques.

        Args:
        - `token` (str): The token to lemmatize.
        - `lang` (str): The language of the token.

        Returns:
        - Optional[str]: The lemma of the token, or None if no lemma is found.

        """
        # filters
        if token.isnumeric():
            return token

        return (
            # supervised searches
            self._dictionary_lookup.get_lemma(token, lang)
            or self._hyphen_search.get_lemma(token, lang)
            or self._rules_search.get_lemma(token, lang)
            or self._prefix_search.get_lemma(token, lang)
            # weakly supervised / greedier searches
            or self._affix_search.get_lemma(token, lang)
        )
