"""Top-level package for Simplemma."""

__title__ = "simplemma"
__author__ = "Adrien Barbaresi"
__email__ = "barbaresi@bbaw.de"
__license__ = "MIT"
__version__ = "0.9.0"


from .dictionary_factory import DictionaryFactory
from .tokenizer import Tokenizer
from .lemmatizer import Lemmatizer
from .language_detector import LaguageDetector

from .dictionary_pickler import *
