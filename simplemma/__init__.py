"""Top-level package for Simplemma.

This package provides simple and lightweight tools for language detection and lemmatization.

Modules:
    language_detector: Module for language detection functionality.
    lemmatizer: Module for lemmatization functionality.
    tokenizer: Module for tokenization functionality.
    token_sampler: Module for token sampling functionality.

"""

from .__metadata__ import __title__, __author__, __email__, __license__, __version__
from .language_detector import LanguageDetector, in_target_language, langdetect
from .lemmatizer import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from .token_sampler import (
    BaseTokenSampler,
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
    TokenSampler,
)
from .tokenizer import RegexTokenizer, Tokenizer, simple_tokenizer

__all__ = [
    "__title__",
    "__author__",
    "__email__",
    "__license__",
    "__version__",
    "LanguageDetector",
    "in_target_language",
    "langdetect",
    "Lemmatizer",
    "is_known",
    "lemma_iterator",
    "lemmatize",
    "text_lemmatizer",
    "BaseTokenSampler",
    "MostCommonTokenSampler",
    "RelaxedMostCommonTokenSampler",
    "TokenSampler",
    "RegexTokenizer",
    "Tokenizer",
    "simple_tokenizer",
]
