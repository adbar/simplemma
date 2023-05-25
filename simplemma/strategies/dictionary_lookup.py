"""
Dictionary Lookup Strategy
--------------------------

This module defines the `DictionaryLookupStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using dictionary lookup.

Module Dependencies:
- typing.Optional: For representing an optional return value.

Class:
- `DictionaryLookupStrategy`: A lemmatization strategy based on dictionary lookup.

"""

from typing import Optional

from .dictionaries.dictionary_factory import DictionaryFactory, DefaultDictionaryFactory
from .lemmatization_strategy import LemmatizationStrategy


class DictionaryLookupStrategy(LemmatizationStrategy):
    """
    Dictionary Lookup Strategy

    This class represents a lemmatization strategy that performs lemmatization by looking up words in a dictionary.
    It implements the `LemmatizationStrategy` protocol.

    Methods:
    - `get_lemma`: Get the lemma for a given token and language using dictionary lookup.

    """

    __slots__ = ["_dictionary_factory"]

    def __init__(
        self, dictionary_factory: DictionaryFactory = DefaultDictionaryFactory()
    ):
        """
        Initialize the Dictionary Lookup Strategy.

        Args:
        - `dictionary_factory` (DictionaryFactory): The dictionary factory used to obtain language dictionaries.
            Defaults to `DefaultDictionaryFactory()`.
        """
        self._dictionary_factory = dictionary_factory

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get Lemma using Dictionary Lookup

        This method performs lemmatization by looking up the token in the language-specific dictionary.
        It returns the lemma if found, or `None` if not found.

        Args:
        - `token` (str): The input token to lemmatize.
        - `lang` (str): The language code for the token's language.

        Returns:
        - Optional[str]: The lemma for the token, or `None` if not found in the dictionary.

        """
        # Search the language data, reverse case to extend coverage.
        dictionary = self._dictionary_factory.get_dictionary(lang)
        if token in dictionary:
            return dictionary[token]
        # Try upper or lowercase.
        token = token.lower() if token[0].isupper() else token.capitalize()
        return dictionary.get(token)
