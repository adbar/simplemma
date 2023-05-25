"""
Tokenizers module. Provides classes for text tokenization.

Classes:
- Tokenizer: An abstract base class for tokenizers.
- RegexTokenizer: A tokenizer that uses regular expressions for tokenization.

Functions:
- simple_tokenizer: A simple tokenizer based on regular expressions.

TODO ADD TOKREGEX
"""

import re
import sys

from abc import abstractmethod
from typing import Iterator, List, Pattern

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

TOKREGEX = re.compile(
    r"(?:"
    r"(?:[€$￥£+-]?[0-9][0-9.,:%/-]*|St\.)[\w_€-]+|"
    r"https?://[^ ]+|"
    r"[€$￥£@#§]?\w[\w*_-]*|"
    r"[,;:\.?!¿¡‽⸮…()\[\]–{}—―/‒_“„”⹂‚‘’‛′″‟'\"«»‹›<>=+−×÷•·]+"
    r")"
)


def simple_tokenizer(text: str, splitting_regex: Pattern[str] = TOKREGEX) -> List[str]:
    """
    Simple regular expression tokenizer.

    This function takes a string as input and returns a list of tokens.

    Args:
        text (str): The input text to tokenize.
        splitting_regex (Pattern[str], optional): The regular expression pattern used for tokenization.
            Defaults to `TOKREGEX`.

    Returns:
        List[str]: The list of tokens extracted from the input text.

    """
    return list(RegexTokenizer(splitting_regex).split_text(text))


class Tokenizer(Protocol):
    """
    Abstract base class for tokenizers.

    Tokenizers are used to split a text into individual tokens.

    Methods:
        split_text(text: str) -> List[str]:
            Splits the text into tokens using the specified regular expression pattern.

    """

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

    Args:
        splitting_regex (Pattern[str], optional): The regular expression pattern used for tokenization.
            Defaults to `TOKREGEX`.

    Methods:
        split_text(text: str) -> List[str]:
            Splits the text into tokens using the specified regular expression pattern.
    """

    __slots__ = ["_splitting_regex"]

    def __init__(self, splitting_regex: Pattern[str] = TOKREGEX) -> None:
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
