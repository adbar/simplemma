from typing import Optional

from .dictionaries.dictionary_factory import DictionaryFactory, DefaultDictionaryFactory

from .lemmatization_strategy import LemmatizationStrategy
from .dictionary_lookup import DictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .rules import RulesStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .affix_decomposition import AffixDecompositionStrategy


class DefaultStrategy(LemmatizationStrategy):
    __slots__ = [
        "_dictionary_lookup",
        "_hyphen_search",
        "_rules_search",
        "_prefix_search",
        "_greedy_dictionary_lookup",
        "_affix_search",
    ]

    def __init__(
        self,
        greedy: bool = False,
        dictionary_factory: DictionaryFactory = DefaultDictionaryFactory(),
    ):
        self._greedy = greedy
        self._dictionary_lookup = DictionaryLookupStrategy(dictionary_factory)
        self._hyphen_search = HyphenRemovalStrategy(self._dictionary_lookup)
        self._rules_search = RulesStrategy()
        self._prefix_search = PrefixDecompositionStrategy(
            dictionary_lookup=self._dictionary_lookup
        )
        greedy_dictionary_lookup = GreedyDictionaryLookupStrategy(dictionary_factory)
        self._affix_search = AffixDecompositionStrategy(
            greedy, self._dictionary_lookup, greedy_dictionary_lookup
        )

        self._greedy_dictionary_lookup = greedy_dictionary_lookup if greedy else None

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        # filters
        if token.isnumeric():
            return token

        candidate = (
            # supervised searches
            self._dictionary_lookup.get_lemma(token, lang)
            or self._hyphen_search.get_lemma(token, lang)
            or self._rules_search.get_lemma(token, lang)
            or self._prefix_search.get_lemma(token, lang)
            # weakly supervised / greedier searches
            or self._affix_search.get_lemma(token, lang)
        )

        # additional round
        if candidate is not None and self._greedy_dictionary_lookup is not None:
            candidate = self._greedy_dictionary_lookup.get_lemma(candidate, lang)

        return candidate
