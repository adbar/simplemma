"""
This module defines the `LemmatizationFallbackStrategy` protocol, which represents the interface for lemmatization fallback strategies in the Simplemma library.
`LemmatizationFallbackStrategy` are used as a fallback strategy when a token's lemma cannot be determined using other lemmatization strategies.
"""

from abc import abstractmethod

from typing import Protocol


class LemmatizationFallbackStrategy(Protocol):
    """
    This protocol defines the interface for lemmatization fallback strategies in the Simplemma library.
    Fallback strategies are used when a token's lemma cannot be determined using other lemmatization strategies.

     Note:
         This protocol should be implemented by concrete fallback strategy classes.
         Concrete implementations of this protocol should provide a concrete implementation for the `get_lemma` method.
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
