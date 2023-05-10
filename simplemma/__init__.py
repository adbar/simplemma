"""Top-level package for Simplemma."""

__title__ = "simplemma"
__author__ = "Adrien Barbaresi"
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
from .dictionary_factory import DictionaryFactory, DefaultDictionaryFactory
from .dictionary_pickler import *
