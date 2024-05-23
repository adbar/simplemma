"""
Lemmatizer module.
Provides classes for lemmatizing token and full texts.

- [Lemmatizer][simplemma.lemmatizer.Lemmatizer]: Class for performing token and full text lemmatization.
- [is_known()][simplemma.lemmatizer.is_known]: A legacy function that wraps the Lemmatizer's [is_known()][simplemma.lemmatizer.Lemmatizer.is_known] method.
- [lemmatize()][simplemma.lemmatizer.lemmatize]: A legacy function that wraps the Lemmatizer's [lemmatize()][simplemma.lemmatizer.Lemmatizer.lemmatize] method.
- [text_lemmatizer()][simplemma.lemmatizer.text_lemmatizer]: A legacy function that wraps the Lemmatizer's [text_lemmatizer()][simplemma.lemmatizer.Lemmatizer.get_lemmas_in_text] method.
- [lemma_iterator()][simplemma.lemmatizer.lemma_iterator]: A legacy function that wraps the Lemmatizer's [lemma_iterator()][simplemma.lemmatizer.Lemmatizer.get_lemmas_in_text] method.
"""

from functools import lru_cache
from typing import Any, Iterator, List, Tuple, Union

from .strategies import (
    DefaultDictionaryFactory,
    DefaultStrategy,
    DictionaryLookupStrategy,
    LemmatizationFallbackStrategy,
    LemmatizationStrategy,
    ToLowercaseFallbackStrategy,
)
from .tokenizer import RegexTokenizer, Tokenizer
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


class Lemmatizer:
    """Lemmatizer class for performing token lemmatization."""

    __slots__ = [
        "_cached_lemmatize",
        "_fallback_lemmatization_strategy",
        "_lemmatization_strategy",
        "_tokenizer",
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
        self._cached_lemmatize = lru_cache(maxsize=cache_max_size)(self._lemmatize)

    def lemmatize(
        self,
        token: str,
        lang: Union[str, Tuple[str, ...]],
    ) -> str:
        """Get the lemmatized form of a given word in the specified language(s).

        Args:
            token: The token to lemmatize.
            lang: The language or languages for lemmatization.

        Returns:
            str: The lemmatized form of the token.
        """
        return self._cached_lemmatize(token, lang)

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


# From here down are legacy function pre-1.0

_legacy_dictionary_factory = DefaultDictionaryFactory()
_legacy_lemmatizer = Lemmatizer(
    lemmatization_strategy=DefaultStrategy(
        dictionary_factory=_legacy_dictionary_factory
    )
)
_legacy_greedy_lemmatizer = Lemmatizer(
    lemmatization_strategy=DefaultStrategy(
        greedy=True, dictionary_factory=_legacy_dictionary_factory
    )
)


def is_known(token: str, lang: Union[str, Tuple[str, ...]]) -> bool:
    """Check if a token is known in the specified language(s).

    Args:
        token: The token to check.
        lang: The language or languages to check in.

    Returns:
        bool: True if the token is known, False otherwise.
    """

    _control_input_type(token)
    lang = validate_lang_input(lang)

    dictionary_lookup = DictionaryLookupStrategy(_legacy_dictionary_factory)
    return any(
        dictionary_lookup.get_lemma(token, lang_code) is not None for lang_code in lang
    )


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
    lemmatizer = _legacy_lemmatizer if not greedy else _legacy_greedy_lemmatizer
    return lemmatizer.lemmatize(token, lang)


def text_lemmatizer(
    text: str, lang: Union[str, Tuple[str, ...]], greedy: bool = False
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
        )
    )


def lemma_iterator(
    text: str, lang: Union[str, Tuple[str, ...]], greedy: bool = False
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
    lemmatizer = _legacy_lemmatizer if not greedy else _legacy_greedy_lemmatizer
    return lemmatizer.get_lemmas_in_text(text, lang)
