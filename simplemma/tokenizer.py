"""Parts related to tokenization."""

import re

from typing import Iterator, List, Match, Union


TOKREGEX = re.compile(
    r"(?:"
    r"(?:[€$￥£+-]?[0-9][0-9.,:%/-]*|St\.)[\w_€-]+|"
    r"https?://[^ ]+|"
    r"[€$￥£@#§]?\w[\w*_-]*|"
    r"[,;:\.?!¿¡‽⸮…()\[\]–{}—―/‒_“„”⹂‚‘’‛′″‟'\"«»‹›<>=+−×÷•·]+"
    r")"
)


def simple_tokenizer(
    text: str, iterate: bool = False
) -> Union[Iterator[Match[str]], List[str]]:
    """Simple regular expression.
    Takes a string as input and returns a list of tokens.
    Provided for convenience and educational purposes."""
    if iterate is False:
        return TOKREGEX.findall(text)
    return TOKREGEX.finditer(text)
