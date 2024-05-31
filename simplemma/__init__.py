"""Top-level package for Simplemma.

This package provides simple and lightweight tools for language detection and lemmatization.

Modules:
    language_detector: Module for language detection functionality.
    lemmatizer: Module for lemmatization functionality.
    tokenizer: Module for tokenization functionality.
    token_sampler: Module for token sampling functionality.

"""

__title__ = "simplemma"
__author__ = "Adrien Barbaresi, Juanjo Diaz and contributors"
__email__ = "barbaresi@bbaw.de"
__license__ = "MIT"
__version__ = "1.0.0"


from .language_detector import LanguageDetector, in_target_language, langdetect
from .lemmatizer import Lemmatizer, is_known, lemma_iterator, lemmatize, text_lemmatizer
from .token_sampler import (
    BaseTokenSampler,
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
    TokenSampler,
)
from .tokenizer import RegexTokenizer, Tokenizer, simple_tokenizer
