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

from typing import Protocol

# Combining marks -- re's \w excludes category M: Latin/Greek/Cyrillic
# diacritics (NFD input), Arabic harakat, Devanagari vowel signs and virama.
_MARKS = (
    "\u0300-\u036f"
    "\u064b-\u065f\u0670"
    "\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962-\u0963"
)

TOKREGEX = re.compile(
    r"(?:"
    r"(?:[€$￥£+-]?[0-9][0-9.,:%/-]*|St\.)(?:[\w_€-]|['’](?=[^\W\d_]))+|"
    r"https?://[^ ]+|"
    # In-word joiners kept for the clitic/boundary strategies: letter-flanked
    # apostrophes (l'homme, 2020'de; a digit after excludes ca "l'1"), combining
    # marks (_MARKS), and ZWNJ between word chars (fa) -- never at a token edge.
    rf"[€$￥£@#§]?\w(?:[\w{_MARKS}*_-]|['’](?=[^\W\d_])|\u200c(?=\w))*|"
    # one punctuation char, or a run of the SAME char ('...', '--', '!!')
    r"([,;:\.?!¿¡‽⸮…։՝।॥،؛؟()\[\]–{}—―/‒_“„”⹂‚‘’‛′″‟'`\"«»‹›<>=+−×÷•·%&№*#°‐-])\1*"
    r")"
)
"""The regular expresion used by default by [RegexTokenizer][simplemma.tokenizer.RegexTokenizer]."""


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

    __slots__ = ["_splitting_regex"]

    def __init__(self, splitting_regex: re.Pattern[str] = TOKREGEX) -> None:
        self._splitting_regex = splitting_regex

    def split_text(self, text: str) -> Iterator[str]:
        """
        Split the input text using the specified regex pattern.

        Args:
            text (str): The input text to tokenize.

        Returns:
            Iterator[str]: An iterator yielding the individual tokens.

        """
        return (match[0] for match in self._splitting_regex.finditer(text))


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
