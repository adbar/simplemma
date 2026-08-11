"""Rule-based lemmatization strategy."""

from collections.abc import Callable

from .defaultrules import RULE_FUNCTIONS
from .lemmatization_strategy import LemmatizationStrategy


class RulesStrategy(LemmatizationStrategy):
    """Apply per-language suffix-replacement rules to unknown tokens."""

    __slots__ = ["_rules"]

    def __init__(self, rules: dict[str, Callable[[str], str | None]] = RULE_FUNCTIONS):
        self._rules = rules

    def get_lemma(self, token: str, lang: str) -> str | None:
        rule_fn = self._rules.get(lang)
        return rule_fn(token) if rule_fn is not None else None
