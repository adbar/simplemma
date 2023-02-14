"""Top-level package for Simplemma."""

__title__ = "simplemma"
__author__ = "Adrien Barbaresi"
__email__ = "barbaresi@bbaw.de"
__license__ = "MIT"
__version__ = "0.9.1"


from .language_detector import in_target_language, lang_detector
from .lemmatizer import lemmatize, lemma_iterator, text_lemmatizer, is_known
from .tokenizer import simple_tokenizer
from .token_sampler import TokenSampler
from .dictionary_factory import DictionaryFactory
from .dictionary_pickler import *
