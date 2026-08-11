"""
Lemmatizer module.
Provides classes for lemmatizing token and full texts.

- [Lemmatizer][simplemma.lemmatizer.Lemmatizer]: Class for performing token and full text lemmatization.
- [is_known()][simplemma.lemmatizer.is_known]: A legacy function that checks whether a token is present in the language data.
- [lemmatize()][simplemma.lemmatizer.lemmatize]: A legacy function that wraps the Lemmatizer's [lemmatize()][simplemma.lemmatizer.Lemmatizer.lemmatize] method.
- [text_lemmatizer()][simplemma.lemmatizer.text_lemmatizer]: A legacy function that wraps the Lemmatizer's [text_lemmatizer()][simplemma.lemmatizer.Lemmatizer.get_lemmas_in_text] method.
- [lemma_iterator()][simplemma.lemmatizer.lemma_iterator]: A legacy function that wraps the Lemmatizer's [lemma_iterator()][simplemma.lemmatizer.Lemmatizer.get_lemmas_in_text] method.
"""

from functools import lru_cache
from typing import Any
from collections.abc import Iterator

from .casing import SentenceCasing, SupportsMembership
from .strategies import (
    DEFAULT_DICTIONARY_FACTORY,
    DefaultStrategy,
    DictionaryLookupStrategy,
    LemmatizationFallbackStrategy,
    LemmatizationStrategy,
    ToLowercaseFallbackStrategy,
)
from .strategies.dictionaries import LOW_MEMORY_DICTIONARY_FACTORY
from .tokenizer import RegexTokenizer, Tokenizer
from .utils import normalize_token, validate_lang_input


def _control_input_type(token: Any) -> None:
    """Check the type of the input token.

    Args:
        token: The input token to check.

    Raises:
        TypeError: If the token is not a string.
        ValueError: If the token is an empty string.
    """

    if not isinstance(token, str):
        raise TypeError(f"Wrong input type, expected string, got {type(token)}")
    if token == "":
        raise ValueError("Wrong input value: empty string")


class Lemmatizer:
    """Lemmatizer class for performing token lemmatization."""

    __slots__ = [
        "_cached_lemmatize",
        "_fallback_lemmatization_strategy",
        "_lemmatization_strategy",
        "_member",
        "_tokenizer",
    ]

    def __init__(
        self,
        cache_max_size: int = 65536,
        tokenizer: Tokenizer = RegexTokenizer(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
        fallback_lemmatization_strategy: LemmatizationFallbackStrategy = ToLowercaseFallbackStrategy(),
    ) -> None:
        """
        Initialize the Lemmatizer.

        Args:
            cache_max_size (int, optional): The maximum size of the cache for the lemmatization results.
                Defaults to `65536`.
            tokenizer (Tokenizer, optional): The tokenizer to use for tokenization.
                Defaults to `RegexTokenizer()`.
            lemmatization_strategy (LemmatizationStrategy, optional): The lemmatization strategy to use.
                Defaults to `DefaultStrategy()`.
            fallback_lemmatization_strategy (LemmatizationFallbackStrategy, optional): The fallback lemmatization strategy to use.
                Defaults to `ToLowercaseFallbackStrategy()`.

        """
        self._tokenizer = tokenizer
        self._lemmatization_strategy = lemmatization_strategy
        self._fallback_lemmatization_strategy = fallback_lemmatization_strategy
        # A strategy exposing raw membership enables the gated/acronym casing
        # heuristics; others fall back to base initial-lowering.
        self._member = (
            lemmatization_strategy.is_dictionary_member
            if isinstance(lemmatization_strategy, SupportsMembership)
            else None
        )
        self._cached_lemmatize = lru_cache(maxsize=cache_max_size)(self._lemmatize)

    def lemmatize(
        self,
        token: str,
        lang: str | tuple[str, ...],
    ) -> str:
        """Get the lemmatized form of a given word in the specified language(s).

        Args:
            token: The token to lemmatize.
            lang: The language or languages for lemmatization.

        Returns:
            str: The lemmatized form of the token.
        """
        # NFC before caching: canonical key, matches the NFC dictionaries.
        return self._cached_lemmatize(normalize_token(token), lang)

    def _lemmatize(
        self,
        token: str,
        lang: str | tuple[str, ...],
    ) -> str:
        """Internal method to lemmatize a token in the specified language(s).

        The token arrives NFC-normalized by ``lemmatize``. Input validation
        happens here so it only runs on cache misses, keeping hits cheap
        (exceptions are never cached by ``lru_cache``).

        Args:
            token: The token to lemmatize.
            lang: The language or languages for lemmatization.

        Returns:
            str: The lemmatized form of the token.
        """
        _control_input_type(token)
        lang = validate_lang_input(lang)

        for lang_code in lang:
            candidate = self._lemmatization_strategy.get_lemma(token, lang_code)
            if candidate is not None:
                return candidate

        return self._fallback_lemmatization_strategy.get_lemma(token, next(iter(lang)))

    def get_lemmas_in_text(
        self,
        text: str,
        lang: str | tuple[str, ...],
    ) -> Iterator[str]:
        """Get an iterator over lemmatized tokens in a text.

        With several languages, the casing heuristics (sentence-initial
        lowering, acronym keeping) follow the first one; lemma lookup
        still tries all of them in order.

        Args:
            text: The text to process.
            lang: The language or languages for lemmatization.

        Yields:
            str: The lemmatized tokens in the text.
        """
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


_LOOKUP_DEFAULT = DictionaryLookupStrategy(DEFAULT_DICTIONARY_FACTORY)
_LOOKUP_LOW_MEM = DictionaryLookupStrategy(LOW_MEMORY_DICTIONARY_FACTORY)


def is_known(token: str, lang: str | tuple[str, ...], low_memory: bool = False) -> bool:
    """Check if a token is known in the specified language(s).

    Args:
        token: The token to check.
        lang: The language or languages to check in.
        low_memory: Use the memory-frugal dictionary backend (default: False).

    Returns:
        bool: True if the token is known, False otherwise.
    """
    _control_input_type(token)
    token = normalize_token(token)
    lang = validate_lang_input(lang)
    lookup = _LOOKUP_LOW_MEM if low_memory else _LOOKUP_DEFAULT
    return any(lookup.get_lemma(token, code) is not None for code in lang)


def lemmatize(
    token: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    low_memory: bool = False,
) -> str:
    """Lemmatize a token in the specified language(s).

    Args:
        token: The token to lemmatize.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).
        low_memory: Use the memory-frugal dictionary backend (default: False).

    Returns:
        str: The lemmatized form of the token.
    """
    return _legacy_lemmatizer_for(greedy, low_memory).lemmatize(token, lang)


def text_lemmatizer(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    low_memory: bool = False,
) -> list[str]:
    """Lemmatize a text in the specified language(s).

    Args:
        text: The text to lemmatize.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).
        low_memory: Use the memory-frugal dictionary backend (default: False).

    Returns:
        list[str]: The list of lemmatized tokens.
    """

    return list(lemma_iterator(text, lang, greedy, low_memory))


def lemma_iterator(
    text: str,
    lang: str | tuple[str, ...],
    greedy: bool = False,
    low_memory: bool = False,
) -> Iterator[str]:
    """Iterate over lemmatized tokens in a text.

    Args:
        text: The text to iterate over.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).
        low_memory: Use the memory-frugal dictionary backend (default: False).

    Yields:
        str: The lemmatized tokens in the text.
    """
    return _legacy_lemmatizer_for(greedy, low_memory).get_lemmas_in_text(text, lang)
