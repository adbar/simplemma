from typing import Dict, Optional, Pattern
from .dictionary_lookup import DictionaryLookupStrategy
from .defaultprefixes import DEFAULT_KNOWN_PREFIXES

from .lemmatization_strategy import LemmatizationStrategy


class PrefixDecompositionStrategy(LemmatizationStrategy):
    __slots__ = ["known_prefixes", "dictionary_lookup"]

    def __init__(
        self,
        known_prefixes: Dict[str, Pattern[str]] = DEFAULT_KNOWN_PREFIXES,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._known_prefixes = known_prefixes
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        "Subword decomposition using pre-defined prefixes (often absent from vocabulary if they are not words)."
        if lang not in self._known_prefixes:
            return None

        prefix_match = self._known_prefixes[lang].match(token)
        if not prefix_match:
            return None
        prefix = prefix_match[1]

        subword = self._dictionary_lookup.get_lemma(
            token[len(prefix) :], lang, dictionary
        )
        if subword is None:
            return None

        return prefix + subword.lower()
