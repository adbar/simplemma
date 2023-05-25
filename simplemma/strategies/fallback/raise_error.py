"""
Raise Error Fallback Strategy
----------------------------

This file defines the `RaiseErrorFallbackStrategy` class, which is a concrete implementation of the `LemmatizationFallbackStrategy` protocol. It represents a fallback strategy that raises a `ValueError` when the lemma of a token cannot be determined.

Classes:
- `RaiseErrorFallbackStrategy`: A concrete implementation of the `LemmatizationFallbackStrategy` protocol.
"""

from .lemmatization_fallback_strategy import LemmatizationFallbackStrategy


class RaiseErrorFallbackStrategy(LemmatizationFallbackStrategy):
    """
    Raise Error Fallback Strategy.

    RaiseErrorFallbackStrategy is a concrete implementation of the LemmatizationFallbackStrategy protocol. It represents
    a fallback strategy that raises a ValueError when the lemma of a token cannot be determined.

    Methods:
    - `get_lemma(token: str, lang: str) -> str`: Raises a ValueError indicating that the token was not found.

    """

    def get_lemma(self, token: str, lang: str) -> str:
        """
        Raise a ValueError indicating that the token was not found.

        This method is called when the lemma of a token cannot be determined using other lemmatization strategies.
        It raises a ValueError with an appropriate error message indicating that the token was not found.

        Args:
            token (str): The token for which the lemma could not be determined.
            lang (str): The language of the token.

        Raises:
            ValueError: The token was not found and its lemma cannot be determined.
        """
        raise ValueError(f"Token not found: {token}")
