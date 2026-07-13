"""
This module defines the `DictionaryLookupStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization using dictionary lookup.
"""

from ..utils import apostrophe_variants
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

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get Lemma using Dictionary Lookup

        This method performs lemmatization by looking up the token in the language-specific dictionary.
        It returns the lemma if found, or `None` if not found.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            str | None: The lemma for the token, or `None` if not found in the dictionary.

        """
        # Search the language data, reverse case to extend coverage.
        dictionary = self._dictionary_factory.get_dictionary(lang)
        for variant in apostrophe_variants(token):
            if (result := dictionary.get(variant)) is not None:
                return result
            # Try upper or lowercase (variant[:1] stays empty-safe for empty input).
            cased = variant.lower() if variant[:1].isupper() else variant.capitalize()
            if (result := dictionary.get(cased)) is not None:
                return result
        return None

    def exact_lemma(self, token: str, lang: str) -> str | None:
        """Case-sensitive lookup (apostrophe variants only, no reverse-case
        fallback): a curated whole-token entry is authoritative over any
        heuristic decomposition of the token."""
        dictionary = self._dictionary_factory.get_dictionary(lang)
        for variant in apostrophe_variants(token):
            if (result := dictionary.get(variant)) is not None:
                return result
        return None
