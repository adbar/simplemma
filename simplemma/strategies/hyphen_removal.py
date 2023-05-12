import re
from typing import Dict, Optional

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


HYPHENS = {"-", "_"}
HYPHENS_FOR_REGEX = "".join(HYPHENS)
HYPHEN_REGEX = re.compile(rf"([{HYPHENS_FOR_REGEX}])")


class HyphenRemovalStrategy(LemmatizationStrategy):
    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        self.dictionary_lookup = dictionary_lookup

    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        "Remove hyphens to see if a dictionary form can be found."
        token_parts = HYPHEN_REGEX.split(token)
        if len(token_parts) <= 1 or not token_parts[-1]:
            return None

        # try to find a word form without hyphen
        candidate = "".join([t for t in token_parts if t not in HYPHENS]).lower()
        if token[0].isupper():
            candidate = candidate.capitalize()
        if candidate in dictionary:
            return dictionary[candidate]

        # decompose
        last_candidate = self.dictionary_lookup.get_lemma(
            token_parts[-1], lang, dictionary
        )
        if last_candidate is not None:
            token_parts[-1] = last_candidate
            return "".join(token_parts)

        return None
