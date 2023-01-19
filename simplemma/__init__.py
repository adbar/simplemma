"""Top-level package for Simplemma."""

__title__ = "simplemma"
__author__ = "Adrien Barbaresi"
__email__ = "barbaresi@bbaw.de"
__license__ = "MIT"
__version__ = "0.9.0"


from .langdetect import LanguageDetector
from .simplemma import Lemmatizer
from .tokenizer import simple_tokenizer
from .dictionaries import DictionaryCache
from .legacy import (
    is_known,
    lemmatize,
    text_lemmatizer,
    lemma_iterator,
    in_target_language,
    lang_detector,
)
from .dictionary_pickler import *
