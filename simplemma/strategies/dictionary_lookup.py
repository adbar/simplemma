"""
This module defines the `DictionaryLookupStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using dictionary lookup.
"""

from typing import Optional

from .dictionaries.dictionary_factory import DefaultDictionaryFactory, DictionaryFactory
from .lemmatization_strategy import LemmatizationStrategy


class DictionaryLookupStrategy(LemmatizationStrategy):
    """Dictionary Lookup Strategy"""

    __slots__ = ["_dictionary_factory"]

    def __init__(
        self, dictionary_factory: DictionaryFactory = DefaultDictionaryFactory()
    ):
        """
        Initialize the Dictionary Lookup Strategy.

        Args:
            dictionary_factory (DictionaryFactory): The dictionary factory used to obtain language dictionaries.
                Defaults to [`DefaultDictionaryFactory()`][simplemma.strategies.dictionaries.dictionary_factory.DefaultDictionaryFactory].
        """
        self._dictionary_factory = dictionary_factory

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get Lemma using Dictionary Lookup

        This method performs lemmatization by looking up the token in the language-specific dictionary.
        It returns the lemma if found, or `None` if not found.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            Optional[str]: The lemma for the token, or `None` if not found in the dictionary.

        """
        # Search the language data, reverse case to extend coverage.
        dictionary = self._dictionary_factory.get_dictionary(lang)
        if result := dictionary.get(token):
            return result
        # Try upper or lowercase.
        token = token.lower() if token[0].isupper() else token.capitalize()
        return dictionary.get(token)
