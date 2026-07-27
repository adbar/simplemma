"""
Tokenizers module.
Provides classes for text tokenization.

- [Tokenizer][simplemma.tokenizer.Tokenizer]: The Protocol class for all tokenizers.
- [RegexTokenizer][simplemma.tokenizer.RegexTokenizer]: A tokenizer based on a regular expresion.
- [simple_tokenizer()][simplemma.tokenizer.simple_tokenizer]: A legacy function that wraps the RegexTokenizer's [split_text][simplemma.tokenizer.RegexTokenizer.split_text] method.
- [TOKREGEX][simplemma.tokenizer.RegexTokenizer]: The regular expresion used by default by [RegexTokenizer][simplemma.tokenizer.RegexTokenizer].
"""

import re
from abc import abstractmethod
from collections.abc import Iterator
from operator import itemgetter

from typing import Protocol

from .utils import _ARMENIAN_MARKS

# currency that glues to a number or word (ONE set for all four regex classes)
_CURRENCY = "€$￥£"

# currency that is punctuation only, never glued
_CURRENCY_PUNCT = "¢¥₩֏₪₹₽₴₺₾"

# non-word chars the word body absorbs, so they can never end a token
_WORD_BODY_EXTRAS = "*_־-"

_PUNCT = (
    ",;:.?!¿¡…։՝।॥،؛؟()[]–{}—―/‒"
    "“„”‚‘’‛′″'`\"«»‹›"
    "<>=+−×÷•·%&№#°׳״‐"
    + _ARMENIAN_MARKS
    + _CURRENCY
    + _CURRENCY_PUNCT
    + _WORD_BODY_EXTRAS
)

# derived, not listed: test_tokenizer brute-forces this against TOKREGEX
_TRAILING_PUNCT = (
    frozenset(_PUNCT) - frozenset(_CURRENCY) - frozenset(_WORD_BODY_EXTRAS)
)

# Combining marks \w excludes (category M): Latin/Greek/Cyrillic, Arabic,
# Devanagari, Hebrew (points/accents; excludes the 4 non-mark codepoints in
# the U+0591-05C7 span: maqaf/paseq/sof-pasuq/nun-hafukha are punctuation),
# Malayalam (vowel signs/anusvara/visarga/virama/length mark; excludes the 2
# Lo letters U+0D3D avagraha and U+0D4E dot reph in the same span).
_MARKS = (
    "\u0300-\u036f"
    "\u064b-\u065f\u0670"
    "\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962-\u0963"
    "\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7"
    "\u0d00-\u0d03\u0d3b-\u0d3c\u0d3e-\u0d44\u0d46-\u0d48\u0d4a-\u0d4d\u0d57\u0d62-\u0d63"
)

TOKREGEX = re.compile(
    r"(?:"
    rf"(?:[{_CURRENCY}+-]?[0-9][0-9.,:%/-]*|St\.)(?:[\w_€-]|['’](?=[^\W\d_]))+|"
    r"https?://[^ ]+|"
    # In-word joiners: apostrophes (l'homme), he geresh/gershayim + ASCII
    # quote (both flanks Hebrew), hy intonation marks, ca ela geminada
    # (l-flanked; U+00B7 elsewhere separates), marks, ZWNJ (fa).
    rf"[{_CURRENCY}@#§]?\w(?:[\w{_MARKS}{_WORD_BODY_EXTRAS}]|['’׳״{_ARMENIAN_MARKS}](?=[^\W\d_])|·(?<=[lL]·)(?=[lL])|\"(?<=[\u05d0-\u05ea]\")(?=[\u05d0-\u05ea])|\u200c(?=\w))*[{_CURRENCY}]?|"
    # one punctuation char, or a run of the SAME char ('...', '--', '!!')
    rf"([{re.escape(_PUNCT)}])\1*"
    r")"
)
"""The regular expresion used by default by [RegexTokenizer][simplemma.tokenizer.RegexTokenizer].

Characters outside the word and punctuation sets -- emoji, arrows and other
symbols -- match no branch and are not emitted as tokens.
"""


_BLOCK = 65536  # process a block of text at a time: bounded memory


def _fast_split(text: str) -> Iterator[str]:
    # pure-alpha chunks, and words with one trailing punct char, skip the regex
    finditer = TOKREGEX.finditer
    start = 0
    length = len(text)
    while start < length:
        end = text.find(" ", start + _BLOCK)
        if end == -1:
            end = length
        for chunk in text[start:end].split(" "):
            if chunk.isalpha():
                yield chunk
            elif chunk:
                if chunk[-1] in _TRAILING_PUNCT and chunk[:-1].isalpha():
                    yield chunk[:-1]
                    yield chunk[-1]
                else:
                    for match in finditer(chunk):
                        yield match[0]
        start = end + 1


class Tokenizer(Protocol):
    """
    Abstract base class for Tokenizers.
    Tokenizers are used to split a text into individual tokens.
    """

    __slots__ = ()

    @abstractmethod
    def split_text(self, text: str) -> Iterator[str]:
        """
        Split the input text into tokens.

        Args:
            text (str): The input text to tokenize.

        Returns:
            Iterator[str]: An iterator yielding the individual tokens.

        """
        raise NotImplementedError


class RegexTokenizer(Tokenizer):
    """
    Tokenizer that uses regular expressions to split a text into tokens.
    This tokenizer splits the input text using the specified regex pattern.
    """

    __slots__ = ["_fast", "_splitting_regex"]

    def __init__(self, splitting_regex: re.Pattern[str] = TOKREGEX) -> None:
        self._splitting_regex = splitting_regex
        # by pattern, not identity: unpickling breaks `is TOKREGEX`
        self._fast = (
            splitting_regex.pattern == TOKREGEX.pattern
            and splitting_regex.flags == TOKREGEX.flags
        )

    def split_text(self, text: str) -> Iterator[str]:
        """
        Split the input text using the specified regex pattern.

        Args:
            text (str): The input text to tokenize.

        Returns:
            Iterator[str]: An iterator yielding the individual tokens.

        """
        if self._fast:
            return _fast_split(text)
        # map+itemgetter measures ~5% faster than a genexpr here
        return map(itemgetter(0), self._splitting_regex.finditer(text))


_legacy_tokenizer = RegexTokenizer()


def simple_tokenizer(text: str) -> list[str]:
    """
    Simple regular expression tokenizer.

    This function takes a string as input and returns a list of tokens.

    Args:
        text (str): The input text to tokenize.

    Returns:
        list[str]: The list of tokens extracted from the input text.

    """
    return list(_legacy_tokenizer.split_text(text))
