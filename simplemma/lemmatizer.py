"""
This module implements a Lemmatizer class and related functions for lemmatizing tokens and text in various languages.

Classes:
- Lemmatizer: A class that provides lemmatization functionality using different strategies.

Functions:
- is_known: Check if a token is known in the given language(s).
- lemmatize: Lemmatize a token in the given language(s).
- text_lemmatizer: Lemmatize text in the given language(s).
- lemma_iterator: Iterate over lemmatized tokens in the given text.
"""

from functools import lru_cache
from typing import Any, List, Iterator, Tuple, Union


from .strategies import (
    LemmatizationStrategy,
    DefaultStrategy,
    DictionaryLookupStrategy,
    LemmatizationFallbackStrategy,
    ToLowercaseFallbackStrategy,
)
from .tokenizer import Tokenizer, RegexTokenizer
from .utils import validate_lang_input

PUNCTUATION = {".", "?", "!", "…", "¿", "¡"}


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
        raise ValueError("Wrong input type: empty string")


def is_known(
    token: str,
    lang: Union[str, Tuple[str, ...]],
) -> bool:
    """Check if a token is known in the specified language(s).

    Args:
        token: The token to check.
        lang: The language or languages to check in.

    Returns:
        bool: True if the token is known, False otherwise.
    """

    return Lemmatizer().is_known(token, lang)


def lemmatize(
    token: str, lang: Union[str, Tuple[str, ...]], greedy: bool = False
) -> str:
    """Lemmatize a token in the specified language(s).

    Args:
        token: The token to lemmatize.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).

    Returns:
        str: The lemmatized form of the token.
    """
    return Lemmatizer(
        lemmatization_strategy=DefaultStrategy(greedy),
    ).lemmatize(token, lang)


def text_lemmatizer(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    tokenizer: Tokenizer = RegexTokenizer(),
) -> List[str]:
    """Lemmatize a text in the specified language(s).

    Args:
        text: The text to lemmatize.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).
        tokenizer: The tokenizer to use (default: RegexTokenizer()).

    Returns:
        List[str]: The list of lemmatized tokens.
    """

    return list(
        lemma_iterator(
            text,
            lang,
            greedy,
            tokenizer=tokenizer,
        )
    )


def lemma_iterator(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    tokenizer: Tokenizer = RegexTokenizer(),
) -> Iterator[str]:
    """Iterate over lemmatized tokens in a text.

    Args:
        text: The text to iterate over.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).
        tokenizer: The tokenizer to use (default: RegexTokenizer()).

    Yields:
        str: The lemmatized tokens in the text.
    """

    return Lemmatizer(
        tokenizer=tokenizer,
        lemmatization_strategy=DefaultStrategy(greedy),
    ).get_lemmas_in_text(text, lang)


class Lemmatizer:
    """Lemmatizer class for performing token lemmatization.

    Methods:
        is_known(token: str, lang: Union[str, Tuple[str, ...]]) -> bool:
            Checks if a token is known in a given language.
        lemmatize(token: str, lang: Union[str, Tuple[str, ...]]) -> str:
            Lemmatizes a token in a given language.
        get_lemmas_in_text(text: str, lang: Union[str, Tuple[str, ...]]) -> Iterator[str]:
            Returns an iterator over the lemmas in a text in a given language.
    """

    __slots__ = [
        "_fallback_lemmatization_strategy",
        "_lemmatization_strategy",
        "_tokenizer",
        "lemmatize",
    ]

    def __init__(
        self,
        cache_max_size: int = 1048576,
        tokenizer: Tokenizer = RegexTokenizer(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
        fallback_lemmatization_strategy: LemmatizationFallbackStrategy = ToLowercaseFallbackStrategy(),
    ) -> None:
        """
        Initialize the Lemmatizer.

        Args:
            cache_max_size (int, optional): The maximum size of the cache for the lemmatization results.
                Defaults to `1048576`.
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
        self.lemmatize = lru_cache(maxsize=cache_max_size)(self._lemmatize)

    def is_known(
        self,
        token: str,
        lang: Union[str, Tuple[str, ...]],
    ) -> bool:
        """Check if a token is known in the specified language(s).

        Args:
            token: The token to check.
            lang: The language or languages to check in.

        Returns:
            bool: True if the token is known, False otherwise.
        """

        _control_input_type(token)
        lang = validate_lang_input(lang)

        dictionary_lookup = DictionaryLookupStrategy()
        return any(
            dictionary_lookup.get_lemma(token, lang_code) is not None
            for lang_code in lang
        )

    def _lemmatize(
        self,
        token: str,
        lang: Union[str, Tuple[str, ...]],
    ) -> str:
        """Internal method to lemmatize a token in the specified language(s).

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
        lang: Union[str, Tuple[str, ...]],
    ) -> Iterator[str]:
        """Get an iterator over lemmatized tokens in a text.

        Args:
            text: The text to process.
            lang: The language or languages for lemmatization.

        Yields:
            str: The lemmatized tokens in the text.
        """
        initial = True
        for token in self._tokenizer.split_text(text):
            yield self.lemmatize(token.lower() if initial else token, lang)
            initial = token in PUNCTUATION
