from typing import Dict, Optional

from .lemmatization_strategy import LemmatizationStrategy
from .dictionary_lookup import DictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .rules import RulesStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .affix_decomposition import AffixDecompositionStrategy

SHORTER_GREEDY = {"bg", "et", "fi"}


class DefaultStrategy(LemmatizationStrategy):
    def __init__(self, greedy: bool = False):
        self.greedy = greedy

    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        # filters
        if token.isnumeric():
            return token

        limit = 6 if lang in SHORTER_GREEDY else 8

        dictionary_lookup = DictionaryLookupStrategy()
        hyphen_search = HyphenRemovalStrategy()
        rules_search = RulesStrategy()
        prefix_search = PrefixDecompositionStrategy()
        greedy_dictionary_lookup = GreedyDictionaryLookupStrategy()
        affix_search = AffixDecompositionStrategy(self.greedy, limit)

        candidate = (
            # supervised searches
            dictionary_lookup.get_lemma(token, lang, dictionary)
            or hyphen_search.get_lemma(token, lang, dictionary)
            or rules_search.get_lemma(token, lang, dictionary)
            or prefix_search.get_lemma(token, lang, dictionary)
            # weakly supervised / greedier searches
            or affix_search.get_lemma(token, lang, dictionary)
        )

        # additional round
        if candidate is not None and self.greedy and len(token) > limit:
            candidate = greedy_dictionary_lookup.get_lemma(candidate, lang, dictionary)

        return candidate
