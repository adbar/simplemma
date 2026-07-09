"""
Lemmatizer module.
Provides classes for lemmatizing token and full texts.

- [Lemmatizer][simplemma.lemmatizer.Lemmatizer]: Class for performing token and full text lemmatization.
- [is_known()][simplemma.lemmatizer.is_known]: A legacy function that checks whether a token is present in the language data.
- [lemmatize()][simplemma.lemmatizer.lemmatize]: A legacy function that wraps the Lemmatizer's [lemmatize()][simplemma.lemmatizer.Lemmatizer.lemmatize] method.
- [text_lemmatizer()][simplemma.lemmatizer.text_lemmatizer]: A legacy function that wraps the Lemmatizer's [text_lemmatizer()][simplemma.lemmatizer.Lemmatizer.get_lemmas_in_text] method.
- [lemma_iterator()][simplemma.lemmatizer.lemma_iterator]: A legacy function that wraps the Lemmatizer's [lemma_iterator()][simplemma.lemmatizer.Lemmatizer.get_lemmas_in_text] method.
"""

import re
from functools import lru_cache
from typing import Any
from collections.abc import Iterator

from .strategies import (
    DefaultDictionaryFactory,
    DefaultStrategy,
    DictionaryLookupStrategy,
    LemmatizationFallbackStrategy,
    LemmatizationStrategy,
    ToLowercaseFallbackStrategy,
)
from .tokenizer import RegexTokenizer, Tokenizer
from .utils import normalize_token, validate_lang_input

PUNCTUATION = {".", "?", "!", "…", "¿", "¡"}

# Languages where lowercasing a sentence-initial token would mangle proper
# nouns; disjoint from BETTER_LOWER (see GH#93).
GATED_INITIAL_LOWERING_LANGS = frozenset({"da", "de", "en"})

# Languages where an ALL-CAPS token is likely an acronym, kept verbatim
# instead of lemmatized. Deliberately overlaps BETTER_LOWER -- bypassing that
# fallback for acronyms is the point (GH#93).
ALLCAPS_KEEP_LANGS = frozenset({"ca", "de", "es", "hy", "lt", "lv", "pt", "uk"})
ALLCAPS_SHOUTING_THRESHOLD = 0.5

# Roman numerals (XI, MCM...) aren't acronyms.
_ROMAN_NUMERAL = re.compile(r"M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")


def _is_keepable_allcaps(token: str) -> bool:
    """ALL-CAPS token worth keeping verbatim as a likely acronym."""
    return (
        len(token) >= 2
        and token.isalpha()
        and token.isupper()
        and not _ROMAN_NUMERAL.fullmatch(token)
    )


def _keep_as_acronym(
    token: str, initial: bool, shouting: bool, strategy: DefaultStrategy, lang0: str
) -> bool:
    """Whether to yield this ALL-CAPS token verbatim instead of lemmatizing.
    Initial position also requires neither its Titlecase (e.g. BERLIN) nor
    lowercase form to be a dictionary entry, else the D' gate runs instead."""
    if shouting or not _is_keepable_allcaps(token):
        return False
    if not initial:
        return True
    return not strategy.is_dictionary_member(
        token.capitalize(), lang0
    ) and not strategy.is_dictionary_member(token.lower(), lang0)


def _initial_surface(token: str, gated: DefaultStrategy | None, lang0: str) -> str:
    """Surface form for a sentence-initial token under the D' gate (GH#93)."""
    lowered = token.lower()
    if gated is None or token.isupper() or gated.is_dictionary_member(lowered, lang0):
        return lowered
    return token  # keep case (likely a proper noun)


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

        Args:
            text: The text to process.
            lang: The language or languages for lemmatization.

        Yields:
            str: The lemmatized tokens in the text.
        """
        langs = validate_lang_input(lang)
        strategy = self._lemmatization_strategy
        # Gating needs DefaultStrategy's dictionary; others keep the plain rule.
        gated = (
            strategy
            if langs[0] in GATED_INITIAL_LOWERING_LANGS
            and isinstance(strategy, DefaultStrategy)
            else None
        )
        # Only validated on the default pipeline, same guard as above.
        if langs[0] in ALLCAPS_KEEP_LANGS and isinstance(strategy, DefaultStrategy):
            yield from self._get_lemmas_allcaps_gated(
                text, lang, langs[0], gated, strategy
            )
            return
        initial = True
        for token in self._tokenizer.split_text(text):
            surface = _initial_surface(token, gated, langs[0]) if initial else token
            yield self.lemmatize(surface, lang)
            initial = token in PUNCTUATION

    def _get_lemmas_allcaps_gated(
        self,
        text: str,
        lang: str | tuple[str, ...],
        lang0: str,
        gated: DefaultStrategy | None,
        strategy: DefaultStrategy,
    ) -> Iterator[str]:
        """Same as `get_lemmas_in_text`, buffered one sentence at a time so
        acronym-keep can see the whole sentence's shouting ratio first.
        Not constant-memory, unlike the default path."""
        sentence: list[str] = []
        for token in self._tokenizer.split_text(text):
            sentence.append(token)
            if token in PUNCTUATION:
                yield from self._lemmatize_sentence(
                    sentence, lang, lang0, gated, strategy
                )
                sentence = []
        if sentence:
            yield from self._lemmatize_sentence(sentence, lang, lang0, gated, strategy)

    def _lemmatize_sentence(
        self,
        tokens: list[str],
        lang: str | tuple[str, ...],
        lang0: str,
        gated: DefaultStrategy | None,
        strategy: DefaultStrategy,
    ) -> Iterator[str]:
        n_alpha = n_shout = 0
        for token in tokens:
            if token.isalpha():
                n_alpha += 1
                # counts Roman numerals too -- don't fold into _is_keepable_allcaps
                if len(token) >= 2 and token.isupper():
                    n_shout += 1
        shouting = not n_alpha or n_shout / n_alpha >= ALLCAPS_SHOUTING_THRESHOLD
        for i, token in enumerate(tokens):
            if _keep_as_acronym(token, i == 0, shouting, strategy, lang0):
                yield normalize_token(token)
            elif i == 0:
                yield self.lemmatize(_initial_surface(token, gated, lang0), lang)
            else:
                yield self.lemmatize(token, lang)


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
_legacy_dictionary_lookup = DictionaryLookupStrategy(_legacy_dictionary_factory)


def is_known(token: str, lang: str | tuple[str, ...]) -> bool:
    """Check if a token is known in the specified language(s).

    Args:
        token: The token to check.
        lang: The language or languages to check in.

    Returns:
        bool: True if the token is known, False otherwise.
    """

    _control_input_type(token)
    token = normalize_token(token)
    lang = validate_lang_input(lang)

    return any(
        _legacy_dictionary_lookup.get_lemma(token, lang_code) is not None
        for lang_code in lang
    )


def lemmatize(token: str, lang: str | tuple[str, ...], greedy: bool = False) -> str:
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
    text: str, lang: str | tuple[str, ...], greedy: bool = False
) -> list[str]:
    """Lemmatize a text in the specified language(s).

    Args:
        text: The text to lemmatize.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).

    Returns:
        list[str]: The list of lemmatized tokens.
    """

    return list(
        lemma_iterator(
            text,
            lang,
            greedy,
        )
    )


def lemma_iterator(
    text: str, lang: str | tuple[str, ...], greedy: bool = False
) -> Iterator[str]:
    """Iterate over lemmatized tokens in a text.

    Args:
        text: The text to iterate over.
        lang: The language or languages for lemmatization.
        greedy: A flag indicating whether to use greedy lemmatization (default: False).

    Yields:
        str: The lemmatized tokens in the text.
    """
    lemmatizer = _legacy_lemmatizer if not greedy else _legacy_greedy_lemmatizer
    return lemmatizer.get_lemmas_in_text(text, lang)
