"""Simplemma strategies module"""

from .dictionaries import DictionaryFactory, DefaultDictionaryFactory

from .lemmatization_strategy import LemmatizationStrategy
from .dictionary_lookup import DictionaryLookupStrategy
from .hyphen_removal import HyphenRemovalStrategy
from .rules import RulesStrategy
from .prefix_decomposition import PrefixDecompositionStrategy
from .greedy_dictionary_lookup import GreedyDictionaryLookupStrategy
from .affix_decomposition import AffixDecompositionStrategy
from .default import DefaultStrategy

from .fallback.lemmatization_fallback_strategy import LemmatizationFallbackStrategy
from .fallback.to_lowercase import ToLowercaseFallbackStrategy
from .fallback.raise_error import RaiseErrorFallbackStrategy
