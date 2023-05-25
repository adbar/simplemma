"""
Affix Decomposition Strategy
----------------------------

This file defines the `AffixDecompositionStrategy` class, which implements an affix decomposition lemmatization strategy in the Simplemma library.

Classes:
- `AffixDecompositionStrategy`: A lemmatization strategy that uses affix decomposition to find lemmas of tokens.
"""

import sys
from typing import Optional
from abc import abstractmethod

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class LemmatizationStrategy(Protocol):
    """
    Lemmatization Strategy Protocol

    This protocol defines the interface for lemmatization strategies. Subclasses implementing this protocol
    must provide an implementation for the `get_lemma` method.

    Methods:
    - `get_lemma`: Get the lemma for a given token and language.

    """

    @abstractmethod
    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get Lemma

        This method receives a token and a language code and should return the lemma for the token in the specified language.
        If the lemma is not found, it should return `None`.

        Args:
        - `token` (str): The input token to lemmatize.
        - `lang` (str): The language code for the token's language.

        Returns:
        - Optional[str]: The lemma for the token, or `None` if not found.

        Raises:
        - NotImplementedError: If the method is not implemented by the subclass.

        """
        raise NotImplementedError()
