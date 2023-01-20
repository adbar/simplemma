"""Top-level package for Simplemma."""

__title__ = "simplemma"
__author__ = "Adrien Barbaresi"
__email__ = "barbaresi@bbaw.de"
__license__ = "MIT"
__version__ = "0.9.1"


from .langdetect import in_target_language, lang_detector
from .simplemma import lemmatize, lemma_iterator, text_lemmatizer, is_known
from .tokenizer import simple_tokenizer
