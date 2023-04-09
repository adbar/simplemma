from typing import Dict, Optional

from .lemmatization_strategy import LemmatizationStrategy


class DictionaryLookupStrategy(LemmatizationStrategy):
    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        "Search the language data, reverse case to extend coverage."
        if token in dictionary:
            return dictionary[token]
        # try upper or lowercase
        token = token.lower() if token[0].isupper() else token.capitalize()
        return dictionary.get(token)
