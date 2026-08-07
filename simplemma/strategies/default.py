"""
This module defines the `DefaultStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using a combination of different strategies such as dictionary lookup, apostrophe-boundary splitting, clitic decomposition, hyphen removal, rule-based lemmatization, prefix decomposition, and affix decomposition.
"""

from .affix_decomposition import AffixDecompositionStrategy
from .apostrophe_boundary import ApostropheBoundaryStrategy
from .clitic_decomposition import CliticDecompositionStrategy
from .dictionaries import LOW_MEMORY_DICTIONARY_FACTORY
from .dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DictionaryFactory,
)
from .dictionary_lookup import DictionaryLookupStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .lemmatization_strategy import LemmatizationStrategy
from .morpheme_decomposition import MorphemeDecompositionStrategy
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
        "_clitic_search",
        "_apostrophe_search",
        "_greedy_dictionary_lookup",
        "_affix_search",
        "_morpheme_search",
    ]

    def __init__(
        self,
        greedy: bool = False,
        dictionary_factory: DictionaryFactory | None = None,
        low_memory: bool = False,
    ):
        """
        Initialize the Default Strategy.

        Args:
            greedy (bool): Whether to use a greedy approach for dictionary lookup. Defaults to `False`.
            dictionary_factory (DictionaryFactory | None): A factory for creating dictionaries.
                Defaults to the shared `DEFAULT_DICTIONARY_FACTORY`, or to
                `LOW_MEMORY_DICTIONARY_FACTORY` if `low_memory` is set.
            low_memory (bool): Use the memory-frugal dictionary backend. Not allowed
                together with `dictionary_factory`. Defaults to `False`.

        Raises:
            ValueError: If both `dictionary_factory` and `low_memory=True` are given.

        """
        if dictionary_factory is None:
            dictionary_factory = (
                LOW_MEMORY_DICTIONARY_FACTORY
                if low_memory
                else DEFAULT_DICTIONARY_FACTORY
            )
        elif low_memory:
            raise ValueError(
                "low_memory selects a dictionary_factory automatically; "
                "pass one or the other, not both"
            )
        self._dictionary_lookup = DictionaryLookupStrategy(dictionary_factory)
        self._hyphen_search = HyphenRemovalStrategy(self._dictionary_lookup)
        self._rules_search = RulesStrategy()
        self._prefix_search = PrefixDecompositionStrategy(
            dictionary_lookup=self._dictionary_lookup
        )
        self._clitic_search = CliticDecompositionStrategy(self._dictionary_lookup)
        # Callback is the search chain, not get_lemma: avoids a circular
        # construction dependency and a second greedy round on the head.
        self._apostrophe_search = ApostropheBoundaryStrategy(
            self._search_pipeline, self._dictionary_lookup
        )
        self._affix_search = AffixDecompositionStrategy(greedy, self._dictionary_lookup)
        self._morpheme_search = MorphemeDecompositionStrategy(self._dictionary_lookup)
        self._greedy_dictionary_lookup = (
            GreedyDictionaryLookupStrategy(dictionary_factory) if greedy else None
        )

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get the lemma for a given token and language using the combination of different lemmatization techniques.

        Args:
            token (str): The token to lemmatize.
            lang (str): The language of the token.

        Returns:
            str | None: The lemma of the token, or None if no lemma is found.

        """
        candidate = self._search_pipeline(token, lang)

        # additional round, applied exactly once regardless of path
        if candidate is not None and self._greedy_dictionary_lookup is not None:
            candidate = self._greedy_dictionary_lookup.get_lemma(candidate, lang)

        return candidate

    def _search_pipeline(self, token: str, lang: str) -> str | None:
        """Run the ordered search chain (no greedy round). Shared by
        `get_lemma` and injected as the apostrophe-boundary head callback."""
        if token.isnumeric():
            return token

        return (
            # before dictionary_lookup: its reverse-case fallback else
            # mangles capitalized proper nouns (Erdoğan'ın -> erdoğan)
            self._apostrophe_search.get_lemma(token, lang)
            or self._dictionary_lookup.get_lemma(token, lang)
            # before hyphen_search: a hyphenated clitic's last part often
            # self-resolves, so hyphen_search would return the token as-is
            or self._clitic_search.get_lemma(token, lang)
            or self._hyphen_search.get_lemma(token, lang)
            or self._rules_search.get_lemma(token, lang)
            or self._prefix_search.get_lemma(token, lang)
            or self._affix_search.get_lemma(token, lang)
            or self._morpheme_search.get_lemma(token, lang)
        )

    def is_dictionary_member(self, token: str, lang: str) -> bool:
        """Raw dictionary membership for `token` (no case/apostrophe fallback)."""
        return self._dictionary_lookup.is_dictionary_member(token, lang)
