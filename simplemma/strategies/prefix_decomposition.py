"""
This module defines the `PrefixDecompositionStrategy` class, which is a concrete implementation of the `LemmatizationStrategy` protocol.
It provides lemmatization by performing subword decomposition using pre-defined prefixes.
"""

import re

from ..utils import canonicalize_token
from .defaultprefixes import DEFAULT_KNOWN_PREFIXES, DROP_PREFIX_LANGS
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


class PrefixDecompositionStrategy(LemmatizationStrategy):
    """
    This class represents a lemmatization strategy that performs lemmatization by performing subword decomposition using pre-defined prefixes.
    It implements the `LemmatizationStrategy` protocol.
    """

    __slots__ = ["_known_prefixes", "_dictionary_lookup"]

    def __init__(
        self,
        known_prefixes: dict[str, re.Pattern[str]] = DEFAULT_KNOWN_PREFIXES,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        """
        Initialize the Prefix Decomposition Strategy.

        Args:
            known_prefixes (dict[str, re.Pattern[str]]): A dictionary of known prefixes for various languages.
                Defaults to `DEFAULT_KNOWN_PREFIXES`.
            dictionary_lookup (DictionaryLookupStrategy): The dictionary lookup strategy used to find dictionary forms.
                Defaults to `DictionaryLookupStrategy()`.

        """
        self._known_prefixes = known_prefixes
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
        """
        Get Lemma using Prefix Decomposition Strategy

        This method performs lemmatization by performing subword decomposition using pre-defined prefixes.
        It checks if the language has known prefixes defined.
        If a known prefix is found at the start of the token, it extracts the prefix and performs dictionary lookup on the remaining subword.
        If a lemma is found for the subword, it returns the prefix plus the lowercase subword -- except for
        `DROP_PREFIX_LANGS`, where the prefix is a separate particle and the subword's lemma alone is returned.
        If no known prefix is found or no lemma is found for the subword, None is returned.

        Args:
            token (str): The input token to lemmatize.
            lang (str): The language code for the token's language.

        Returns:
            str | None: The lemma for the token, or None if no lemma is found.

        """
        if lang not in self._known_prefixes:
            return None

        # Fold BEFORE matching (no-op for unregistered langs): ar tashkeel
        # sits between a fused prefix's letters (بِالْكِتَابِ), so a
        # multi-char prefix can never match the raw token.
        token = canonicalize_token(token, lang)
        prefix_match = self._known_prefixes[lang].match(token)
        if not prefix_match or prefix_match[1] == token:
            return None

        prefix = prefix_match[1]

        subword = self._dictionary_lookup.get_lemma(token[len(prefix) :], lang)
        if not subword:
            return None

        # DROP_PREFIX_LANGS: the prefix is its own particle, so the stem's
        # lemma alone is the answer -- see the module comment above.
        if lang in DROP_PREFIX_LANGS:
            return subword

        return prefix + subword.lower()
