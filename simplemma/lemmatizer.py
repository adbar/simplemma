"""Main module."""

from functools import lru_cache
from typing import Any, List, Iterator, Tuple, Union


from .strategies.lemmatization_strategy import LemmatizationStrategy
from .strategies.default import DefaultStrategy
from .strategies.dictionary_lookup import DictionaryLookupStrategy
from .strategies.fallback.lemmatization_fallback_strategy import (
    LemmatizationFallbackStrategy,
)
from .strategies.fallback.default import DefaultFallbackStrategy

from .dictionary_factory import DictionaryFactory
from .tokenizer import Tokenizer

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
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
) -> bool:
    return Lemmatizer(dictionary_factory=dictionary_factory).is_known(token, lang)


def lemmatize(
    token: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
) -> str:
    return Lemmatizer(
        dictionary_factory=dictionary_factory,
        lemmatization_strategy=DefaultStrategy(greedy),
    ).lemmatize(token, lang)


def text_lemmatizer(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    tokenizer: Tokenizer = Tokenizer(),
) -> List[str]:
    return list(
        lemma_iterator(
            text,
            lang,
            greedy,
            dictionary_factory=dictionary_factory,
            tokenizer=tokenizer,
        )
    )


def lemma_iterator(
    text: str,
    lang: Union[str, Tuple[str, ...]],
    greedy: bool = False,
    dictionary_factory: DictionaryFactory = DictionaryFactory(),
    tokenizer: Tokenizer = Tokenizer(),
) -> Iterator[str]:
    return Lemmatizer(
        dictionary_factory=dictionary_factory,
        tokenizer=tokenizer,
        lemmatization_strategy=DefaultStrategy(greedy),
    ).get_lemmas_in_text(text, lang)


class Lemmatizer:
    __slots__ = [
        "dictionary_factory",
        "fallback_lemmatization_strategy",
        "lemmatize",
        "lemmatization_strategy",
        "tokenizer",
    ]

    def __init__(
        self,
        cache_max_size: int = 1048576,
        dictionary_factory: DictionaryFactory = DictionaryFactory(),
        tokenizer: Tokenizer = Tokenizer(),
        lemmatization_strategy: LemmatizationStrategy = DefaultStrategy(),
        fallback_lemmatization_strategy: LemmatizationFallbackStrategy = DefaultFallbackStrategy(),
    ) -> None:
        self.dictionary_factory = dictionary_factory
        self.tokenizer = tokenizer
        self.lemmatization_strategy = lemmatization_strategy
        self.fallback_lemmatization_strategy = fallback_lemmatization_strategy
        self.lemmatize = lru_cache(maxsize=cache_max_size)(self._lemmatize)

    def is_known(
        self,
        token: str,
        lang: Union[str, Tuple[str, ...]],
    ) -> bool:
        """Tell if a token is present in one of the loaded dictionaries.
        Case-insensitive, whole word forms only. Returns True or False."""
        _control_input_type(token)
        dictionaries = self.dictionary_factory.get_dictionaries(lang)

        dictionary_lookup = DictionaryLookupStrategy()
        return any(
            dictionary_lookup.get_lemma(token, lang_code, lang_dictionary) is not None
            for lang_code, lang_dictionary in dictionaries.items()
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
        dictionaries = self.dictionary_factory.get_dictionaries(lang)

        for lang_code, lang_dictionary in dictionaries.items():
            candidate = self.lemmatization_strategy.get_lemma(
                token, lang_code, lang_dictionary
            )
            if candidate is not None:
                return candidate

        return self.fallback_lemmatization_strategy.get_lemma(
            token, next(iter(dictionaries))
        )

    def get_lemmas_in_text(
        self,
        text: str,
        lang: Union[str, Tuple[str, ...]],
    ) -> Iterator[str]:
        """Convenience function to lemmatize a text using a simple tokenizer.
        Returns a list of tokens and lemmata."""
        initial = True
        for token in self.tokenizer.split_text(text):
            yield self.lemmatize(token.lower() if initial else token, lang)
            initial = token in PUNCTUATION
