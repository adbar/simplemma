from typing import Optional

from .dictionaries.dictionary_factory import DictionaryFactory, DefaultDictionaryFactory
from .lemmatization_strategy import LemmatizationStrategy


class DictionaryLookupStrategy(LemmatizationStrategy):
    __slots__ = ["_dictionary_factory"]

    def __init__(
        self, dictionary_factory: DictionaryFactory = DefaultDictionaryFactory()
    ):
        self._dictionary_factory = dictionary_factory

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        "Search the language data, reverse case to extend coverage."
        dictionary = self._dictionary_factory.get_dictionary(lang)
        if token in dictionary:
            return dictionary[token]
        # try upper or lowercase
        token = token.lower() if token[0].isupper() else token.capitalize()
        return dictionary.get(token)
