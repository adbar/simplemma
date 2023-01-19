from .simplemma import Lemmatizer
from .langdetect import LanguageDetector

_lemmatizer = Lemmatizer()
is_known = _lemmatizer.is_known
lemmatize = _lemmatizer.lemmatize
text_lemmatizer = _lemmatizer.text_lemmatizer
lemma_iterator = _lemmatizer.lemma_iterator

_languageDetector = LanguageDetector()
in_target_language = _languageDetector.in_target_language
lang_detector = _languageDetector.lang_detector
