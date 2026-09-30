"""Text tokenization."""

import re
from abc import abstractmethod
from collections.abc import Iterator
from operator import itemgetter

from typing import Protocol

from .utils import _ARMENIAN_MARKS

# currency that stays on a word (R$, US$, $PETR4) but splits off a number
_CURRENCY = "€$£"

# currency that never glues to a word
_CURRENCY_PUNCT = "¢¥￥₩֏₪₹₽₴₺₾"

# non-word chars the word body absorbs, so they never end a token
_WORD_BODY_EXTRAS = "*_־-"

_STANDALONE_PUNCT = (
    ",;:.?!¿¡…։՝।॥،؛؟()[]–{}—―/‒"
    "“„”‚‘’‛′″'`\"«»‹›"
    "<>=+−×÷•·%&№#°׳״‐" + _ARMENIAN_MARKS + _CURRENCY_PUNCT
)

_PUNCT = _STANDALONE_PUNCT + _CURRENCY + _WORD_BODY_EXTRAS

# test_tokenizer brute-forces this split against TOKREGEX
_TRAILING_PUNCT = frozenset(_STANDALONE_PUNCT)

# combining marks \w excludes, gaps skip non-mark codepoints (e.g. Hebrew maqaf)
_MARKS = (
    "\u0300-\u036f"
    "\u064b-\u065f\u0670"
    "\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962-\u0963"
    "\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7"
    "\u0d00-\u0d03\u0d3b-\u0d3c\u0d3e-\u0d44\u0d46-\u0d48\u0d4a-\u0d4d\u0d57\u0d62-\u0d63"
)

TOKREGEX = re.compile(
    r"(?:"
    r"(?:[+-]?[0-9][0-9.,:%/-]*|St\.)(?:[\w-]|['’](?=[^\W\d_]))+|"
    r"https?://\S+|"
    # a sign not on a letter is its own token, '$$' falls to the run branch
    rf"[{_CURRENCY}](?![^\W\d_])(?![{_CURRENCY}])|"
    # in-word joiners: apostrophes, he geresh/quote, hy marks, ca l·l, ZWNJ (fa)
    rf"[{_CURRENCY}@#§]?\w(?:[\w{_MARKS}{_WORD_BODY_EXTRAS}]|['’׳״{_ARMENIAN_MARKS}](?=[^\W\d_])|·(?<=[lL]·)(?=[lL])|\"(?<=[\u05d0-\u05ea]\")(?=[\u05d0-\u05ea])|\u200c(?=\w))*[{_CURRENCY}]?|"
    # one punctuation char, or a run of the same char ('...', '!!')
    rf"([{re.escape(_PUNCT)}])\1*"
    r")"
)
"""Default regex of [RegexTokenizer][simplemma.tokenizer.RegexTokenizer].

Emoji and other symbols outside the word and punctuation sets are dropped.
A currency sign next to a number is its own token (`€3.50`, `50€`).
A sign on a word stays part of it (`R$`, `US$`).
"""


_BLOCK = 65536  # bounded memory
_WHITESPACE = re.compile(r"\s")


def _fast_split(text: str) -> Iterator[str]:
    # pure-alpha chunks and words with one trailing punct char skip the regex
    finditer = TOKREGEX.finditer
    start = 0
    length = len(text)
    while start < length:
        # any whitespace, else newline-separated text is never blocked at all
        boundary = _WHITESPACE.search(text, start + _BLOCK)
        end = boundary.start() if boundary else length
        # split() never yields an empty chunk
        for chunk in text[start:end].split():
            if chunk.isalpha():
                yield chunk
            elif chunk[-1] in _TRAILING_PUNCT and chunk[:-1].isalpha():
                yield chunk[:-1]
                yield chunk[-1]
            else:
                for match in finditer(chunk):
                    yield match[0]
        start = end + 1


class Tokenizer(Protocol):
    """Protocol for text tokenizers."""

    __slots__ = ()

    @abstractmethod
    def split_text(self, text: str) -> Iterator[str]:
        """Yield tokens from `text`."""


class RegexTokenizer(Tokenizer):
    """Tokenizer using a regex pattern (default: `TOKREGEX`)."""

    __slots__ = ["_fast", "_splitting_regex"]

    def __init__(self, splitting_regex: re.Pattern[str] = TOKREGEX) -> None:
        self._splitting_regex = splitting_regex
        # by pattern, not identity: unpickling breaks `is TOKREGEX`
        self._fast = (
            splitting_regex.pattern == TOKREGEX.pattern
            and splitting_regex.flags == TOKREGEX.flags
        )

    def split_text(self, text: str) -> Iterator[str]:
        """Yield tokens from `text`."""
        if self._fast:
            return _fast_split(text)
        return map(itemgetter(0), self._splitting_regex.finditer(text))


_legacy_tokenizer = RegexTokenizer()


def simple_tokenizer(text: str) -> list[str]:
    """Tokenize `text` into a list of strings (legacy wrapper)."""
    return list(_legacy_tokenizer.split_text(text))
