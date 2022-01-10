"""Parts related to tokenization."""

import re


TOKREGEX = re.compile(r'(?:(?:[0-9][0-9.,:%-]*|St\.)[\w_€-]+|https?://[^ ]+|[@#§$]?\w[\w*_-]*|[,;:\.?!¿¡‽⸮…()\[\]–{}—―/‒_“„”⹂‚‘’‛′″‟\'"«»‹›<>=+−×÷•·]+)')


def simple_tokenizer(text):
    """Simple regular expression adapted from NLTK.
       Takes a string as input and returns a list of tokens.
       Provided for convenience and educational purposes."""
    return TOKREGEX.findall(text)
