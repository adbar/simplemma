"""Dictionary lookup lemmatization strategy."""

from ..utils import (
    apostrophe_variants,
    canonicalize_token,
    has_apostrophe,
    has_armenian_marks,
    strip_armenian_marks,
)
from .dictionaries.dictionary_factory import (
    DEFAULT_DICTIONARY_FACTORY,
    DictionaryFactory,
)
from .lemmatization_strategy import LemmatizationStrategy


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
        # no-op for unregistered langs: matches the canonicalization
        # dictionary_builder applies to keys at build time.
        token = canonicalize_token(token, lang)
        # Fast path: apostrophe-free tokens skip the variant machinery (hottest
        # lookup). Reverse case extends coverage; token[:1] is empty-safe.
        if (result := dictionary.get(token)) is not None:
            return result
        cased = token.lower() if token[:1].isupper() else token.capitalize()
        if (result := dictionary.get(cased)) is not None:
            return result
        # hy: fall back to the mark-stripped form
        if lang == "hy" and has_armenian_marks(token):
            stripped = strip_armenian_marks(token)
            if (result := dictionary.get(stripped)) is not None:
                return result
            cased = (
                stripped.lower() if stripped[:1].isupper() else stripped.capitalize()
            )
            return dictionary.get(cased)
        if not has_apostrophe(token):
            return None
        # Remaining variants (typed token was variant[0], probed above).
        for variant in apostrophe_variants(token)[1:]:
            if (result := dictionary.get(variant)) is not None:
                return result
            cased = variant.lower() if variant[:1].isupper() else variant.capitalize()
            if (result := dictionary.get(cased)) is not None:
                return result
        return None

    def exact_lemma(self, token: str, lang: str) -> str | None:
        """Case-sensitive lookup (apostrophe variants only, no reverse-case
        fallback): a curated whole-token entry beats any heuristic decomposition."""
        dictionary = self._dictionary_factory.get_dictionary(lang)
        token = canonicalize_token(token, lang)
        for variant in apostrophe_variants(token):
            if (result := dictionary.get(variant)) is not None:
                return result
        return None

    def is_dictionary_member(self, token: str, lang: str) -> bool:
        """Whether `token` is a literal dictionary key (no case/apostrophe fallback)."""
        token = canonicalize_token(token, lang)
        return self._dictionary_factory.get_dictionary(lang).get(token) is not None
