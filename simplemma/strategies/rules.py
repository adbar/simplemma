from typing import Callable, Dict, Optional
from .defaultrules import DEFAULT_RULES

from .lemmatization_strategy import LemmatizationStrategy


class RulesStrategy(LemmatizationStrategy):
    __slots__ = ["_rules"]

    def __init__(
        self, rules: Dict[str, Callable[[str], Optional[str]]] = DEFAULT_RULES
    ):
        self._rules = rules

    def get_lemma(
        self, token: str, lang: str, dictionary: Dict[str, str]
    ) -> Optional[str]:
        "Pre-defined rules."
        if lang not in self._rules:
            return None

        return self._rules[lang](token)
