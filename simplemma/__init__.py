"""Top-level package for Simplemma."""

__title__ = 'simplemma'
__author__ = 'Adrien Barbaresi'
__email__ = 'barbaresi@bbaw.de'
__license__ = 'MIT'
__version__ = '0.6.0'


from .simplemma import load_data, lemmatize, text_lemmatizer, is_known
from .tokenizer import simple_tokenizer
