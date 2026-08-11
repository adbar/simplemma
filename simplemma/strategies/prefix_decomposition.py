"""Prefix decomposition lemmatization strategy."""

import re

from ..utils import canonicalize_token
from .defaultprefixes import DEFAULT_KNOWN_PREFIXES, DROP_PREFIX_LANGS
from .dictionary_lookup import DictionaryLookupStrategy
from .lemmatization_strategy import LemmatizationStrategy


class PrefixDecompositionStrategy(LemmatizationStrategy):
    """Strip a known prefix, look up the remainder; for DROP_PREFIX_LANGS the
    prefix is a particle (dropped), otherwise it stays attached."""

    __slots__ = ["_known_prefixes", "_dictionary_lookup"]

    def __init__(
        self,
        known_prefixes: dict[str, re.Pattern[str]] = DEFAULT_KNOWN_PREFIXES,
        dictionary_lookup: DictionaryLookupStrategy = DictionaryLookupStrategy(),
    ):
        self._known_prefixes = known_prefixes
        self._dictionary_lookup = dictionary_lookup

    def get_lemma(self, token: str, lang: str) -> str | None:
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
