"""Parts related to tokenization."""

import re

from typing import Iterator, List, Match, Pattern, Union


TOKREGEX = re.compile(
    r"(?:"
    r"(?:[€$￥£+-]?[0-9][0-9.,:%/-]*|St\.)[\w_€-]+|"
    r"https?://[^ ]+|"
    r"[€$￥£@#§]?\w[\w*_-]*|"
    r"[,;:\.?!¿¡‽⸮…()\[\]–{}—―/‒_“„”⹂‚‘’‛′″‟'\"«»‹›<>=+−×÷•·]+"
    r")"
)


def simple_tokenizer(
    text: str, splitting_regex: Pattern[str] = TOKREGEX
) -> Iterator[str]:
    """Simple regular expression.
    Takes a string as input and returns a list of tokens.
    Provided for convenience and educational purposes."""
    return Tokenizer(splitting_regex).get_tokens(text)


class Tokenizer:
    def __init__(self, splitting_regex: Pattern[str] = TOKREGEX) -> None:
        self.splitting_regex = splitting_regex

    def get_tokens(self, text: str) -> Iterator[str]:
        return (match[0] for match in self.splitting_regex.finditer(text))
