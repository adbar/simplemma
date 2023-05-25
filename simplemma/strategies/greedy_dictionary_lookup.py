from .lemmatization_strategy import LemmatizationStrategy
from .dictionaries.dictionary_factory import DictionaryFactory, DefaultDictionaryFactory
from ..utils import levenshtein_dist

SHORTER_GREEDY = {"bg", "et", "fi"}


class GreedyDictionaryLookupStrategy(LemmatizationStrategy):
    __slots__ = ["_dictionary_factory", "_distance", "_steps"]

    def __init__(
        self,
        dictionary_factory: DictionaryFactory = DefaultDictionaryFactory(),
        steps: int = 1,
        distance: int = 5,
    ):
        self._dictionary_factory = dictionary_factory
        self._steps = steps
        self._distance = distance

    def get_lemma(self, token: str, lang: str) -> str:
        "Greedy mode: try further hops, not always a good idea."

        limit = 6 if lang in SHORTER_GREEDY else 8
        if len(token) <= limit:
            return token

        dictionary = self._dictionary_factory.get_dictionary(lang)
        candidate = token
        for _ in range(self._steps):
            if candidate not in dictionary:
                break

            new_candidate = dictionary[candidate]

            if (
                len(new_candidate) > len(candidate)
                or levenshtein_dist(new_candidate, candidate) > self._distance
            ):
                break

            candidate = new_candidate

        return candidate
