"""
This file defines the `LemmatizationStrategy` protocl class, which all lemmatization strategies should extend to be usable by the Simplemma library.
"""

from abc import abstractmethod
from typing import Optional, Protocol


class LemmatizationStrategy(Protocol):
    """
    This protocol defines the interface for lemmatization strategies. Subclasses implementing this protocol
    must provide an implementation for the `get_lemma` method.

    Note:
        This protocol should be implemented by concrete lemmatization strategy classes.
        Concrete implementations of this protocol should provide a concrete implementation for the `get_lemma` method.
    """

    @abstractmethod
    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        This method receives a token and a language code and should return the lemma for the token in the specified language.
        If the lemma is not found, it should return `None`.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            Optional[str]: The lemma for the token, or `None` if not found.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.

        """
        raise NotImplementedError()
