"""
This module defines the `ToLowercaseFallbackStrategy` class, which is a concrete implementation of the `LemmatizationFallbackStrategy` protocol. It represents a fallback strategy that converts tokens to lowercase for specific languages.
"""

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy

# Only where UD gold lowercases proper nouns; elsewhere identity wins held-out
# (es +2.8, lv +1.6, uk +1.2, lt +1.1, pt +1.1, hy +0.6pp, 2026-09).
BETTER_LOWER = {"bg", "sk"}


class ToLowercaseFallbackStrategy(LemmatizationFallbackStrategy):
    """
    ToLowercaseFallbackStrategy is a concrete implementation of the LemmatizationFallbackStrategy protocol.
    It represents a fallback strategy that converts tokens to lowercase for specific languages.
    """

    __slots__ = ["_langs_to_lower"]

    def __init__(self, langs_to_lower: set[str] = BETTER_LOWER):
        """
        Initialize the ToLowercaseFallbackStrategy with the specified set of languages to convert to lowercase.

        Args:
            langs_to_lower (set[str]): The set of languages for which tokens should be converted to lowercase.
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
