"""
To Lowercase Fallback Strategy
------------------------------

This file defines the `ToLowercaseFallbackStrategy` class, which is a concrete implementation of the `LemmatizationFallbackStrategy` protocol. It represents a fallback strategy that converts tokens to lowercase for specific languages.

Classes:
- `ToLowercaseFallbackStrategy`: A concrete implementation of the `LemmatizationFallbackStrategy` protocol.
"""

from typing import Set

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy

BETTER_LOWER = {"bg", "es", "hy", "lt", "lv", "pt", "sk", "uk"}


class ToLowercaseFallbackStrategy(LemmatizationFallbackStrategy):
    """
    To Lowercase Fallback Strategy.

    ToLowercaseFallbackStrategy is a concrete implementation of the LemmatizationFallbackStrategy protocol.
    It represents a fallback strategy that converts tokens to lowercase for specific languages.

    Attributes:
    - `_langs_to_lower` (Set[str]): The set of languages for which tokens should be converted to lowercase.

    Methods:
    - `__init__(langs_to_lower: Set[str] = BETTER_LOWER)`: Initializes the ToLowercaseFallbackStrategy with the specified set of languages to convert to lowercase.
    - `get_lemma(token: str, lang: str) -> str`: Converts the token to lowercase if the language is in the set of languages to convert.

    """

    __slots__ = ["_langs_to_lower"]

    def __init__(self, langs_to_lower: Set[str] = BETTER_LOWER):
        """
        Initialize the ToLowercaseFallbackStrategy with the specified set of languages to convert to lowercase.

        Args:
            langs_to_lower (Set[str]): The set of languages for which tokens should be converted to lowercase.
                Defaults to `BETTER_LOWER`.

        """
        self._langs_to_lower = langs_to_lower

    def get_lemma(self, token: str, lang: str) -> str:
        """
        Convert the token to lowercase if the language is in the set of languages to convert.

        This method is called when the lemma of a token cannot be determined using other lemmatization strategies.
        It converts the token to lowercase if the language is in the set of languages specified during initialization.

        Args:
            token (str): The token for which the lemma could not be determined.
            lang (str): The language of the token.

        Returns:
            str: The lowercase version of the token if the language is in the set of languages to convert,
                 otherwise returns the original token.

        """
        return token.lower() if lang in self._langs_to_lower else token
