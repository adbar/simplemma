from typing import Dict

from .lemmatization_strategy import LemmatizationStrategy
from ..utils import levenshtein_dist


class GreedyDictionaryLookupStrategy(LemmatizationStrategy):
    __slots__ = ["_steps", "_distance"]

    def __init__(self, steps: int = 1, distance: int = 5):
        self._steps = steps
        self._distance = distance

    def get_lemma(self, token: str, lang: str, dictionary: Dict[str, str]) -> str:
        "Greedy mode: try further hops, not always a good idea."
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
