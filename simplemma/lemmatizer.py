"""Lemmatizer can find the lemma of a token using a search strategy.
Lemmatizer can also find the tokens in a text and return the list of lemmas."""

from functools import lru_cache
from typing import Any, List, Iterator, Tuple, Union


from .strategies.lemmatization_strategy import LemmatizationStrategy
from .strategies.default import DefaultStrategy
from .strategies.dictionary_lookup import DictionaryLookupStrategy
from .strategies.fallback.lemmatization_fallback_strategy import (
    LemmatizationFallbackStrategy,
)
from .strategies.fallback.to_lowercase import ToLowercaseFallbackStrategy
from .tokenizer import Tokenizer, RegexTokenizer
from .utils import validate_lang_input

PUNCTUATION = {".", "?", "!", "…", "¿", "¡"}


def _control_input_type(token: Any) -> None:
    "Make sure the input is a string of length > 0."
    if not isinstance(token, str):
        raise TypeError(f"Wrong input type, expected string, got {type(token)}")
    if token == "":
        raise ValueError("Wrong input type: empty string")


def is_known(
    token: str,
    lang: Union[str, Tuple[str, ...]],
) -> bool:
    return Lemmatizer().is_known(token, lang)


def lemmatize(
    token: str, lang: Union[str, Tuple[str, ...]], greedy: bool = False
) -> str:
    return Lemmatizer(
        lemmatization_strategy=DefaultStrategy(greedy),
    ).lemmatize(token, lang)


def text_lemmatizer(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    tokenizer: Tokenizer = RegexTokenizer(),
) -> List[str]:
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
    return Lemmatizer(
        tokenizer=tokenizer,
        lemmatization_strategy=DefaultStrategy(greedy),
    ).get_lemmas_in_text(text, lang)


class Lemmatizer:
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
        self._tokenizer = tokenizer
        self._lemmatization_strategy = lemmatization_strategy
        self._fallback_lemmatization_strategy = fallback_lemmatization_strategy
        self.lemmatize = lru_cache(maxsize=cache_max_size)(self._lemmatize)

    def is_known(
        self,
        token: str,
        lang: Union[str, Tuple[str, ...]],
    ) -> bool:
        """Tell if a token is present in one of the loaded dictionaries.
        Case-insensitive, whole word forms only. Returns True or False."""
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
        """Try to reduce a token to its lemma form according to the
        language list passed as input.
        Returns a string."""
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
        """Convenience function to lemmatize a text using a simple tokenizer.
        Returns a list of tokens and lemmata."""
        initial = True
        for token in self._tokenizer.split_text(text):
            yield self.lemmatize(token.lower() if initial else token, lang)
            initial = token in PUNCTUATION
