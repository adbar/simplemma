"""Lemmatizer module."""

from collections.abc import Callable, Iterator
from functools import lru_cache
from typing import Any

from .casing import MembershipCheck, SentenceCasing
from .strategies import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultStrategy,
    DictionaryLookupStrategy,
    LemmatizationStrategy,
)
from .strategies.dictionaries import LOW_MEMORY_DICTIONARY_FACTORY
from .tokenizer import RegexTokenizer, Tokenizer
from .utils import normalize_token, validate_lang_input

# Only where UD gold lowercases proper nouns; elsewhere identity wins held-out
# (es +2.8, lv +1.6, uk +1.2, lt +1.1, pt +1.1, hy +0.6pp, 2026-09).
BETTER_LOWER = frozenset({"bg", "sk"})


def _default_fallback(token: str, lang: str) -> str:
    """Lowercase the token for BETTER_LOWER languages, return it as-is otherwise."""
    return token.lower() if lang in BETTER_LOWER else token


def _control_input_type(token: Any) -> None:
    """Raise TypeError for a non-string token, ValueError for an empty one."""
    if not isinstance(token, str):
        raise TypeError(f"Wrong input type, expected string, got {type(token)}")
    if token == "":
        raise ValueError("Wrong input value: empty string")


class Lemmatizer:
    """Lemmatizer class for performing token lemmatization."""

    __slots__ = (
        "_cached_lemmatize",
        "_fallback",
        "_lemmatization_strategy",
        "_member",
        "_tokenizer",
    )

    def __init__(
        self,
        cache_max_size: int = 65536,
        tokenizer: Tokenizer = RegexTokenizer(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
        fallback: Callable[[str, str], str] | None = None,
    ) -> None:
        self._tokenizer = tokenizer
        self._lemmatization_strategy = lemmatization_strategy
        self._fallback = fallback or _default_fallback
        # A strategy exposing raw membership (`is_dictionary_member`) enables the
        # gated/acronym casing heuristics; others get base initial-lowering only.
        self._member: MembershipCheck | None = getattr(
            lemmatization_strategy, "is_dictionary_member", None
        )
        self._cached_lemmatize = lru_cache(maxsize=cache_max_size)(self._lemmatize)

    def lemmatize(
        self,
        token: str,
        lang: str | tuple[str, ...],
    ) -> str:
        """Return the lemma of `token` in the given language(s)."""
        # NFC before caching: canonical key, matches the NFC dictionaries.
        return self._cached_lemmatize(normalize_token(token), lang)

    def _lemmatize(
        self,
        token: str,
        lang: str | tuple[str, ...],
    ) -> str:
        """Cache-miss path: validates here so hits stay cheap (the token is
        already NFC from `lemmatize`; lru_cache never caches exceptions)."""
        _control_input_type(token)
        lang = validate_lang_input(lang)

        for lang_code in lang:
            candidate = self._lemmatization_strategy.get_lemma(token, lang_code)
            if candidate is not None:
                return candidate

        return self._fallback(token, next(iter(lang)))

    def get_lemmas_in_text(
        self,
        text: str,
        lang: str | tuple[str, ...],
    ) -> Iterator[str]:
        """Yield lemmatized tokens from `text`."""
        langs = validate_lang_input(lang)
        casing = SentenceCasing(langs[0], self._member)
        for surface, keep in casing.apply(self._tokenizer.split_text(text)):
            # surface arrives NFC, so skip lemmatize()'s re-normalization
            yield surface if keep else self._cached_lemmatize(surface, lang)


# Legacy pre-1.0 functions.


# Cached to keep each Lemmatizer's token cache alive.
@lru_cache(maxsize=None)
def _legacy_lemmatizer_for(greedy: bool, low_memory: bool) -> Lemmatizer:
    return Lemmatizer(
        lemmatization_strategy=DefaultStrategy(greedy=greedy, low_memory=low_memory)
    )


def is_known(token: str, lang: str | tuple[str, ...], low_memory: bool = False) -> bool:
    """Check if a token is present in the language data."""
    _control_input_type(token)
    token = normalize_token(token)
    lang = validate_lang_input(lang)
    lookup = DictionaryLookupStrategy(
        LOW_MEMORY_DICTIONARY_FACTORY if low_memory else DEFAULT_DICTIONARY_FACTORY
    )
    return any(lookup.get_lemma(token, code) is not None for code in lang)


def lemmatize(
    token: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    low_memory: bool = False,
) -> str:
    """Return the lemma of `token` in the given language(s)."""
    return _legacy_lemmatizer_for(greedy, low_memory).lemmatize(token, lang)


def text_lemmatizer(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    low_memory: bool = False,
) -> list[str]:
    """Lemmatize all tokens in `text` and return them as a list."""
    return list(lemma_iterator(text, lang, greedy, low_memory))


def lemma_iterator(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    low_memory: bool = False,
) -> Iterator[str]:
    """Yield lemmatized tokens from `text`."""
    return _legacy_lemmatizer_for(greedy, low_memory).get_lemmas_in_text(text, lang)
