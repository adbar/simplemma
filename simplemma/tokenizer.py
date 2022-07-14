"""Parts related to tokenization."""

import re

from typing import Iterator, List, Match, Union


TOKREGEX = re.compile(
    r'(?:(?:[0-9][0-9.,:%-]*|St\.)[\w_€-]+|https?://[^ ]+|[@#§$]?\w[\w*_-]*|[,;:\.?!¿¡‽⸮…()\[\]–{}—―/‒_“„”⹂‚‘’‛′″‟\'"«»‹›<>=+−×÷•·]+)'
)


def simple_tokenizer(
    text: str, iterate: bool = False
) -> Union[Iterator[Match[str]], List[str]]:
    """Simple regular expression adapted from NLTK.
    Takes a string as input and returns a list of tokens.
    Provided for convenience and educational purposes."""
    if iterate is False:
        return TOKREGEX.findall(text)
    return TOKREGEX.finditer(text)
