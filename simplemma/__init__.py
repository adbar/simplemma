"""Simplemma: fast, dependency-free lemmatization for 54 languages."""

from .__metadata__ import __title__, __author__, __license__, __version__
from .language_detector import LanguageDetector, in_target_language, langdetect
from .lemmatizer import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from .sentences import split_sentences
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
    "split_sentences",
    "BaseTokenSampler",
    "MostCommonTokenSampler",
    "RelaxedMostCommonTokenSampler",
    "TokenSampler",
    "RegexTokenizer",
    "Tokenizer",
    "simple_tokenizer",
]
