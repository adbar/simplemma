"""Dictionary lookup lemmatization strategy."""

from collections.abc import Mapping

from ..utils import _ARMENIAN_MARKS, canonicalize_token
from .dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DictionaryFactory,
)
from .lemmatization_strategy import LemmatizationStrategy

_STRIP_ARMENIAN_MARKS = str.maketrans("", "", _ARMENIAN_MARKS)


def _probe(dictionary: Mapping[str, str], token: str) -> str | None:
    """Look `token` up as typed, then in reverse case (token[:1] is empty-safe)."""
    if (result := dictionary.get(token)) is not None:
        return result
    return dictionary.get(token.lower() if token[:1].isupper() else token.capitalize())


class DictionaryLookupStrategy(LemmatizationStrategy):
    """Dictionary Lookup Strategy"""

    __slots__ = ["_dictionary_factory"]

    def __init__(
        self, dictionary_factory: DictionaryFactory = DEFAULT_DICTIONARY_FACTORY
    ):
        self._dictionary_factory = dictionary_factory

    def get_lemma(self, token: str, lang: str) -> str | None:
        """Return the lemma for `token` in `lang`, or None."""
        dictionary = self._dictionary_factory.get_dictionary(lang)
        # matches the canonicalization dictionary_builder applies to keys
        token = canonicalize_token(token, lang)
        if (result := _probe(dictionary, token)) is not None:
            return result
        # hy: fall back to the intonation-mark-stripped form
        if lang == "hy" and any(mark in token for mark in _ARMENIAN_MARKS):
            return _probe(dictionary, token.translate(_STRIP_ARMENIAN_MARKS))
        return None

    def is_dictionary_member(self, token: str, lang: str) -> bool:
        """Whether `token` is a literal dictionary key (no case fallback)."""
        dictionary = self._dictionary_factory.get_dictionary(lang)
        # not `in`: the Mapping views pay a KeyError on a miss
        return dictionary.get(canonicalize_token(token, lang)) is not None
