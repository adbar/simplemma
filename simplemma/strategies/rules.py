"""
This module defines the `RulesStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization by applying pre-defined rules for each language.
"""

from typing import Callable, Dict, Optional

from .defaultrules import DEFAULT_RULES
from .lemmatization_strategy import LemmatizationStrategy


class RulesStrategy(LemmatizationStrategy):
    """
    This class represents a lemmatization strategy that performs lemmatization by applying pre-defined rules for each language.
    It implements the `LemmatizationStrategy` protocol.
    """

    __slots__ = ["_rules"]

    def __init__(
        self, rules: Dict[str, Callable[[str], Optional[str]]] = DEFAULT_RULES
    ):
        """
        Initialize the Rules Strategy.

        Args:
            rules (Dict[str, Callable[[str], Optional[str]]]): A dictionary of pre-defined rules for various languages.
                Defaults to `DEFAULT_RULES`.

        """
        self._rules = rules

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get Lemma using Rules Strategy

        This method performs lemmatization by applying pre-defined rules for each language.
        It checks if the language has pre-defined rules defined.
        If rules are defined, it applies the corresponding rule on the token to get the lemma.
        If a lemma is found, it is returned.
        If no rules are defined for the language or no lemma is found, None is returned.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            Optional[str]: The lemma for the token, or None if no lemma is found.

        """
        if lang not in self._rules:
            return None

        return self._rules[lang](token)
