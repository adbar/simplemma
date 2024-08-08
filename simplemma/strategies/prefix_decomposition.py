"""
This module defines the `PrefixDecompositionStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization by performing subword decomposition using pre-defined prefixes.
"""

from typing import Dict, Optional, Pattern

from .defaultprefixes import DEFAULT_KNOWN_PREFIXES
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


class PrefixDecompositionStrategy(LemmatizationStrategy):
    """
    This class represents a lemmatization strategy that performs lemmatization by performing subword decomposition using pre-defined prefixes.
    It implements the `LemmatizationStrategy` protocol.
    """

    __slots__ = ["_known_prefixes", "_dictionary_lookup"]

    def __init__(
        self,
        known_prefixes: Dict[str, Pattern[str]] = DEFAULT_KNOWN_PREFIXES,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        """
        Initialize the Prefix Decomposition Strategy.

        Args:
            known_prefixes (Dict[str, Pattern[str]]): A dictionary of known prefixes for various languages.
                Defaults to `DEFAULT_KNOWN_PREFIXES`.
            dictionary_lookup (DictionaryLookupStrategy): The dictionary lookup strategy used to find dictionary forms.
                Defaults to `DictionaryLookupStrategy()`.

        """
        self._known_prefixes = known_prefixes
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get Lemma using Prefix Decomposition Strategy

        This method performs lemmatization by performing subword decomposition using pre-defined prefixes.
        It checks if the language has known prefixes defined.
        If a known prefix is found at the start of the token, it extracts the prefix and performs dictionary lookup on the remaining subword.
        If a lemma is found for the subword, it returns the concatenation of the prefix and the lowercase subword.
        If no known prefix is found or no lemma is found for the subword, None is returned.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            Optional[str]: The lemma for the token, or None if no lemma is found.

        """
        if lang not in self._known_prefixes:
            return None

        prefix_match = self._known_prefixes[lang].match(token)
        if not prefix_match or prefix_match[1] == token:
            return None

        prefix = prefix_match[1]

        subword = self._dictionary_lookup.get_lemma(token[len(prefix) :], lang)

        return prefix + subword.lower() if subword else None
