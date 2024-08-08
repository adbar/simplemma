"""
This module defines the `HyphenRemovalStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization by removing hyphens from tokens and attempting to find dictionary forms.
"""

import re
from typing import Optional

from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy

HYPHENS = {"-", "_"}
HYPHEN_REGEX = re.compile(rf"([{''.join(HYPHENS)}])")


class HyphenRemovalStrategy(LemmatizationStrategy):
    """
    This class represents a lemmatization strategy that performs lemmatization by removing hyphens from tokens
    and attempting to find dictionary forms.
    It implements the `LemmatizationStrategy` protocol.
    """

    __slots__ = ["_dictionary_lookup"]

    def __init__(
        self, dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy()
    ):
        """
        Initialize the Hyphen Removal Strategy.

        Args:
            dictionary_lookup (DictionaryLookupStrategy): The dictionary lookup strategy used to find dictionary forms.
                Defaults to `DictionaryLookupStrategy()`.

        """
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> Optional[str]:
        """
        Get Lemma using Hyphen Removal Strategy

        This method performs lemmatization by removing hyphens from the token and attempting to find a dictionary form.
        It splits the token based on hyphen characters, removes hyphens, and forms a candidate lemma for lookup.
        If a dictionary form is found, it is returned as the lemma.
        If not found, it attempts to decompose the token by looking up the last part (after the last hyphen) in the dictionary.
        If a lemma is found for the last part, it replaces the last part in the token and returns the modified token as the lemma.
        If no dictionary form is found, None is returned.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            Optional[str]: The lemma for the token, or None if no lemma is found.

        """
        token_parts = HYPHEN_REGEX.split(token)
        if len(token_parts) <= 1 or not token_parts[-1]:
            return None

        # try to find a word form without hyphen
        candidate = "".join([t for t in token_parts if t not in HYPHENS]).lower()
        if token[0].isupper():
            candidate = candidate.capitalize()

        lemma = self._dictionary_lookup.get_lemma(candidate, lang)
        if lemma is not None:
            return lemma

        # decompose
        last_part_lemma = self._dictionary_lookup.get_lemma(token_parts[-1], lang)
        if last_part_lemma is not None:
            return "".join(token_parts[:-1] + [last_part_lemma])

        return None
