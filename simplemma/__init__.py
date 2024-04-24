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
__version__ = "0.9.1"


from .language_detector import LanguageDetector, in_target_language, langdetect
from .lemmatizer import Lemmatizer, lemmatize, lemma_iterator, text_lemmatizer, is_known
from .tokenizer import Tokenizer, RegexTokenizer, simple_tokenizer
from .token_sampler import (
    TokenSampler,
    BaseTokenSampler,
    MostCommonTokenSampler,
    RelaxedMostCommonTokenSampler,
)
