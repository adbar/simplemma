"""
Lemmatization Fallback Strategy
-------------------------------

This file defines the `LemmatizationFallbackStrategy` protocol, which represents the interface for lemmatization fallback strategies in the Simplemma library.
`LemmatizationFallbackStrategy` are used as a fallback strategy when a token's lemma cannot be determined using other lemmatization strategies.

Classes:
- `LemmatizationFallbackStrategy`: A protocol defining the interface for lemmatization fallback strategies.

"""

import sys
from abc import abstractmethod

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class LemmatizationFallbackStrategy(Protocol):
    """
    Protocol for Lemmatization Fallback Strategies.

    LemmatizationFallbackStrategy is a protocol that defines the interface for lemmatization fallback strategies
    in the Simplemma library. Fallback strategies are used when a token's lemma cannot be determined using other
    lemmatization strategies.

    Note:
        This protocol should be implemented by concrete fallback strategy classes.

    Methods:
    - `get_lemma(token: str, lang: str) -> str`: Retrieves the lemma of a given token in the specified language.

    """

    @abstractmethod
    def get_lemma(self, token: str, lang: str) -> str:
        """
        Retrieve the lemma of a given token in the specified language.

        This method takes a token and a language and returns the lemma of the token in the specified language.

        Args:
            token (str): The token for which to retrieve the lemma.
            lang (str): The language of the token.

        Returns:
            str: The lemma of the token in the specified language.

        Raises:
            NotImplementedError: This method must be implemented by concrete classes.
        """
        raise NotImplementedError()
